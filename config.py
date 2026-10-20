
"""
config.py

Central configuration for Scripture Overlay.
Import constants from this module throughout the application.
"""

import os
from pathlib import Path


# ============================================================
# Application
# ============================================================

APP_NAME = "Scripture Overlay Backend"

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))

DEBUG = os.getenv("DEBUG", "false").lower() in (
    "true", "1", "yes", "on"
)

THREADED = True

# ============================================================
# Logging
# ============================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

WERKZEUG_LOG_LEVEL = os.getenv(
    "WERKZEUG_LOG_LEVEL", "ERROR"
).upper()


# ============================================================
# Project directories
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
DEBUG_DIR = BASE_DIR / "debug"

SCENE_DIR = STATIC_DIR / "images"

for directory in (DATA_DIR, DEBUG_DIR):
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# Persistent files
# ============================================================

NAV_FILE = DATA_DIR / "scripture_navigation.json"

HISTORY_FILE = DATA_DIR / "scripture_history.json"

SCENE_FILE = DATA_DIR / "scene.json"

DEBUG_FILE = DEBUG_DIR / "debug.html"


# ============================================================
# Bible defaults
# ============================================================

DEFAULT_PROVIDER = os.getenv(
    "DEFAULT_PROVIDER", "biblegateway"
)

DEFAULT_REFERENCE = os.getenv(
    "DEFAULT_REFERENCE", "John 3:16"
)

DEFAULT_VERSION = os.getenv(
    "DEFAULT_VERSION", "KJV"
)

MAX_VERSES = int(os.getenv("MAX_VERSES", "4"))

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))

PROVIDERS = {
    "biblegateway": "BibleGateway",
    "olivetree": "Olive Tree",
    "biblecom": "Bible.com"
}

USER_AGENT = (
    "Mozilla/5.0 "
    "(Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/138.0 Safari/537.36"
)


# ============================================================
# Background scenes
# ============================================================

SCENE_EXTENSIONS = frozenset({
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".avif"
})


# ============================================================
# Environment-based API settings
# ============================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL", "openrouter/free"
)
