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
    request
)

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