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
from biblegateway import BibleGatewayProvider
from biblegateway import BibleGatewayError


###########################################################################
# Configuration
###########################################################################

HOST = "0.0.0.0"

PORT = 8080

DEBUG = False

VERSIONS = {

    "KJV": "King James Version",

    "NKJV": "New King James Version",

    "NIV": "New International Version",

    "ESV": "English Standard Version",

    "NASB": "New American Standard Bible",

    "NLT": "New Living Translation",

    "AMP": "Amplified Bible",

    "CSB": "Christian Standard Bible",

    "MSG": "The Message",

    "GNT": "Good News Translation",

    "AMP": "Amplified Bible",

    "AMPC": "Amplified Bible, Classic Edition",

    "HCSB": "Holman Christian Standard Bible",

    "NET": "New English Translation",

    "RSV": "Revised Standard Version",

    "NRSV": "New Revised Standard Version",  

}


###########################################################################
# Initialise services
###########################################################################

# app = Flask(__name__)
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

import logging

# Suppress Flask's default logging to avoid cluttering the console
logging.getLogger("werkzeug").setLevel(logging.ERROR)

provider = BibleGatewayProvider()

cache = PassageCache()

manager = QuotationManager(
    provider,
    cache
)

###########################################################################
# Utility
###########################################################################

def fetch_scripture():

    """
    Returns the currently selected Scripture.
    """

    passage = manager.get_passage()

    if passage is None:

        raise BibleGatewayError(
            "No Scripture available."
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

# import traceback

@app.route("/scripture")
def scripture():

    try:

        return jsonify(fetch_scripture())

    except BibleGatewayError as exc:

        return jsonify(
            {
                "reference": "",
                "version": "",
                "verses": [],
                "error": str(exc)
            }
        ), 500

    except Exception as exc:

        return jsonify(
            {

                "reference": "",

                "version": "",

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

        "reference": manager.get_reference(),

        "version": manager.get_version()

    })


###########################################################################
# Shutdown
###########################################################################

def shutdown():

    pass




############################################################################
@app.route("/select") # GET method
def select():

    return render_template(

        "select.html",

        versions=VERSIONS,

        reference=manager.get_reference(),

        version=manager.get_version()

    )

@app.route("/select", methods=["POST"])
def update_selection():

    data = request.get_json()

    reference = data["reference"]

    version = data["version"]

    manager.set(

        reference,

        version

    )

    return jsonify({

        "success": True,

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