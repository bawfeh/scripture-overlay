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


###########################################################################
# Configuration
###########################################################################

HOST = "0.0.0.0"

PORT = 8080

DEBUG = False

###########################################################################
# Initialise services
###########################################################################

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

from bible_provider import get_provider

# provider = get_provider("olivetree")

import logging

# Suppress Flask's default logging to avoid cluttering the console
logging.getLogger("werkzeug").setLevel(logging.ERROR)

cache = PassageCache()

manager = QuotationManager( DEFAULT_PROVIDER, cache )

###########################################################################
# Utility
###########################################################################

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
        print(
            f"Success! Scripture for {manager.get_reference()} "
            f"({manager.get_version()}) fetched."
        )

    return passage


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


###########################################################################
# Shutdown
###########################################################################

def shutdown():

    pass


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

    data = request.get_json()

    reference = data["reference"]

    version = data["version"]

    provider = data["provider"]

    manager.set( provider, reference, version )

    return jsonify({

        "success": True,

        "provider" : manager.get_provider_name(),

        "reference": manager.get_reference(),

        "version": manager.get_version()

    })


SCENE_DIR = Path(app.static_folder) / "images"
SCENE_FILE = Path(app.root_path) / "data" / "scene.json"
SCENE_EXTENSIONS = {
    ".png", 
    ".jpg", 
    ".jpeg", 
    ".webp", 
    ".gif",
    ".avif"
}
scene_lock = threading.Lock()


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

        print("Scripture Overlay Backend")

        print("--------------------------------------------")

        print()

        print(f"Host      : {HOST}")

        print(f"Port      : {PORT}")

        print()

        app.run(

            host=HOST,

            port=PORT,

            debug=DEBUG,

            threaded=True

        )

    finally:

        shutdown()