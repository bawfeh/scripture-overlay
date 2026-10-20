"""
app.py

Main backend server for the Scripture Overlay.

Responsibilities
----------------

1. Monitor quotation.txt
2. Read the requested reference/version
3. Retrieve the passage (using cache if possible)
4. Return JSON to the frontend

"""

from pathlib import Path

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    url_for
)

import json
import threading
from quotation_manager import QuotationManager 
from cache import PassageCache 
from bible_provider import DEFAULT_PROVIDER 
from bible_provider import BibleProviderError
from bible_provider import get_provider
import logging
import config
from fetch_history import save_scripture_history
import scripture_navigation as navigation


###########################################################################
# Initialise services
###########################################################################

app = Flask(
    __name__,
    template_folder=str(config.TEMPLATE_DIR),
    static_folder=str(config.STATIC_DIR)
)

# Configure Werkzeug HTTP request logging
logging.getLogger("werkzeug").setLevel(
    getattr(logging, config.WERKZEUG_LOG_LEVEL, logging.ERROR)
)

# Configure application logging
app.logger.setLevel(
    getattr(logging, config.LOG_LEVEL, logging.INFO)
)

cache = PassageCache()

manager = QuotationManager(config.DEFAULT_PROVIDER, cache)

scripture_lock = threading.RLock()

SCENE_DIR = config.SCENE_DIR
SCENE_FILE = config.SCENE_FILE
SCENE_EXTENSIONS = config.SCENE_EXTENSIONS
scene_lock = threading.Lock()

###########################################################################
# Utility
###########################################################################

def available_scenes():
    if not SCENE_DIR.is_dir():
        return []

    return sorted(
        [
            p.name for p in SCENE_DIR.iterdir()
            if p.is_file()
            and p.suffix.lower() in SCENE_EXTENSIONS
        ],
        key=str.casefold
    )


def current_scene():
    scenes = available_scenes()

    if not scenes:
        return None

    try:
        saved = json.loads(
            SCENE_FILE.read_text(encoding="utf-8")
        ).get("scene")
    except (OSError, ValueError, TypeError, AttributeError):
        saved = None

    return saved if saved in scenes else scenes[0]


def restore_last_scripture():
    """
    Restore the active Scripture selection from persistent
    navigation history when the application starts.

    Scripture text is retrieved lazily by /scripture.
    """

    try:
        state = navigation.status()
        entry = state.get("current")

        if not entry:
            app.logger.info(
                "No previous Scripture selection to restore."
            )
            return False

        provider = entry["provider"]
        reference = entry["reference"]
        version = entry["version"]

        with scripture_lock:
            manager.set(
                provider,
                reference,
                version
            )

        app.logger.info(
            "Restored Scripture selection: %s (%s), provider=%s",
            reference,
            version,
            provider
        )

        return True

    except Exception:
        app.logger.exception(
            "Unable to restore previous Scripture selection."
        )
        return False


restore_last_scripture()


def fetch_scripture():

    """
    Returns the currently selected Scripture.
    """
    
    already_cached = False

    try:
        already_cached = manager.is_cached()

        passage = manager.get_passage()

    except BibleProviderError:
        raise

    if passage is None:
        raise BibleProviderError(
            f"No Scripture available for {manager.get_reference()} "
            f"({manager.get_version()})."
        )
    
    if not already_cached:
        save_scripture_history(manager)

        print(
            f"Success! Scripture for {manager.get_reference()} "
            f"({manager.get_version()}) fetched."
        )

    return passage


def shutdown():

    pass


###########################################################################
# Routes
###########################################################################

@app.route("/")
def home():

    """
    Serves index.html.
    """

    return render_template("index.html")


###########################################################################

@app.route("/scripture")
def scripture():

    with scripture_lock:
        
        try:
            return jsonify(fetch_scripture())

        except BibleProviderError as exc:
            if manager.get_reference():
                app.logger.warning("%s", exc)
            return jsonify(
                {
                    "reference": manager.get_reference(),
                    "version": manager.get_version(),
                    "verses": [],
                    "error": str(exc)
                }
            ), 500

        except Exception as exc:
            # app.logger.exception("Unexpected error while retrieving Scripture")
            return jsonify(
                {
                    "reference": manager.get_reference(),
                    "version": manager.get_version(),
                    "verses": [],
                    "error": str(exc)
                }
            ), 500


###########################################################################

@app.route("/health")
def health():

    return jsonify({

        "status": "ok",

        "reference": manager.get_reference(),

        "version": manager.get_version(),

        "cache_entries": cache.size()

    })


###########################################################################

@app.route("/reload")
def reload():

    """
    Clears the passage cache.
    Useful while testing.
    """

    cache.clear()

    return jsonify(
        {

            "status": "Cache cleared"

        }
    )


###########################################################################

@app.get("/scripture/history")
def scripture_history():
    from fetch_history import HISTORY_FILE

    if not HISTORY_FILE.exists():
        return jsonify([])

    with HISTORY_FILE.open("r", encoding="utf-8") as f:
        history = json.load(f)

    return jsonify(history)



###########################################################################

@app.get("/scripture/navigation")
def scripture_navigation_status():
    return jsonify(navigation.status())


@app.post("/scripture/navigation")
def navigate_scripture():

    data = request.get_json(silent=True) or {}
    direction = data.get("direction")

    if direction not in ("back", "forward"):
        return jsonify({
            "success": False,
            "error": "Direction must be 'back' or 'forward'."
        }), 400

    step = -1 if direction == "back" else 1

    with scripture_lock:

        entry = navigation.target(step)

        if entry is None:
            return jsonify({
                "success": False,
                "error": "No Scripture available in that direction."
            }), 409

        previous = {
            "provider": manager.get_provider_name(),
            "reference": manager.get_reference(),
            "version": manager.get_version()
        }

        try:
            # Restore the previous or next Scripture.
            manager.set(
                entry["provider"],
                entry["reference"],
                entry["version"]
            )

            # Retrieve the Scripture from cache or provider.
            passage = fetch_scripture()

            if not passage:
                raise BibleProviderError(
                    "Unable to restore the selected Scripture."
                )

            # Commit navigation only after successful restoration.
            result = navigation.advance(step)

            if result is None:
                raise RuntimeError(
                    "Navigation position could not be updated."
                )

        except Exception as error:

            # Restore the original selection on failure.
            try:
                manager.set(
                    previous["provider"],
                    previous["reference"],
                    previous["version"]
                )
            except Exception:
                app.logger.exception(
                    "Failed to restore the previous selection."
                )

            return jsonify({
                "success": False,
                "error": str(error)
            }), 502

        return jsonify({
            "success": True,
            **result
        })


###########################################################################

@app.route("/quotation")
def quotation():

    """
    Returns the currently selected quotation.

    Mainly for debugging.
    """

    return jsonify({

        "provider": manager.get_provider_name(),

        "reference": manager.get_reference(),

        "version": manager.get_version()

    })


############################################################################
# Scripture selection
############################################################################

@app.route("/versions/<provider>")
def get_versions(provider):

    try:

        bible_provider = get_provider(provider)

        # bible_provider.APP_ROOT = f"http://localhost:{PORT}/"

        return jsonify({

            "success": True,

            "provider": bible_provider.name,

            "versions": bible_provider.get_versions(),

            "default_version": bible_provider.get_default_version(),

            "default_reference": bible_provider.get_default_reference()
        })

    except ValueError as error:

        return jsonify({

            "success": False,

            "error": str(error)

        }), 400

    except BibleProviderError as error:

        return jsonify({

            "success": False,

            "error": str(error)

        }), 502
    
@app.route("/select") # GET method
def select():

    return render_template(

        "select.html",

        reference=manager.get_reference(),

        version=manager.get_version(),

        versions=manager.get_provider_versions(),

        providers=manager.get_providers()
    )


@app.route("/select", methods=["POST"])
def update_selection():

    data = request.get_json(silent=True) or {}

    reference = data.get("reference")
    version = data.get("version")
    provider = data.get("provider")

    if not all([reference, version, provider]):
        return jsonify({
            "success": False,
            "error": "Provider, reference and version are required."
        }), 400

    with scripture_lock:

        # Save the current selection so it can be restored on failure.
        previous = {
            "provider": manager.get_provider_name(),
            "reference": manager.get_reference(),
            "version": manager.get_version()
        }

        try:
            # Set the requested Scripture.
            manager.set(provider, reference, version)

            # Confirm that Scripture can actually be retrieved.
            # This also records a genuine cache miss in fetch_history.
            passage = fetch_scripture()

            if not passage:
                raise BibleProviderError(
                    "Scripture retrieval returned no passage."
                )

            # Only record successful Scripture selections.
            navigation.record(
                manager.get_provider_name(),
                manager.get_reference(),
                manager.get_version()
            )

        except Exception as error:

            # Restore the previous selection.
            try:
                manager.set(
                    previous["provider"],
                    previous["reference"],
                    previous["version"]
                )
            except Exception:
                app.logger.exception(
                    "Unable to restore previous Scripture selection"
                )

            return jsonify({
                "success": False,
                "error": str(error)
            }), 502

        return jsonify({
            "success": True,
            "provider": manager.get_provider_name(),
            "reference": manager.get_reference(),
            "version": manager.get_version()
        })


@app.get("/scenes")
def get_scenes():
    scenes = available_scenes()

    return jsonify({
        "scenes": [
            {
                "name": name,
                "url": url_for(
                    "static",
                    filename=f"images/{name}"
                )
            }
            for name in scenes
        ],
        "selected": current_scene()
    })


@app.get("/scene")
def get_scene():
    return jsonify({
        "scene": current_scene()
    })


@app.post("/scene")
def set_scene():
    payload = request.get_json(silent=True) or {}
    name = payload.get("scene")

    if not isinstance(name, str) or name not in available_scenes():
        return jsonify({
            "success": False,
            "error": "Invalid or unavailable scene."
        }), 400

    with scene_lock:
        SCENE_FILE.parent.mkdir(parents=True, exist_ok=True)

        temp_file = SCENE_FILE.with_suffix(".tmp")
        temp_file.write_text(
            json.dumps({"scene": name}),
            encoding="utf-8"
        )
        temp_file.replace(SCENE_FILE)

    return jsonify({
        "success": True,
        "scene": name
    })

###########################################################################

if __name__ == "__main__":

    try:

        print()
        print("--------------------------------------------")
        print(config.APP_NAME)
        print("--------------------------------------------")
        print()
        print(f"Host      : {config.HOST}")
        print(f"Port      : {config.PORT}")
        print()
        
        app.run(
            host=config.HOST,
            port=config.PORT,
            debug=config.DEBUG,
            threaded=config.THREADED
        )

    finally:

        shutdown()