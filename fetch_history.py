
"""
fetch_history.py

Persist successful Scripture fetch events in a JSON file.
"""

import json
import threading

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


HISTORY_FILE = Path(__file__).resolve().parent.joinpath("data", "scripture_history.json")

TIMEZONE = ZoneInfo("Europe/Oslo")

_history_lock = threading.Lock()


def save_scripture_history(manager):
    """
    Append a Scripture fetch event to the history file.
    """

    record = {
        "success": True,
        "provider": manager.get_provider_name(),
        "reference": manager.get_reference(),
        "version": manager.get_version(),
        "time": datetime.now(TIMEZONE).isoformat(
            timespec="microseconds"
        )
    }

    with _history_lock:

        HISTORY_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if HISTORY_FILE.exists():
            with HISTORY_FILE.open(
                "r",
                encoding="utf-8"
            ) as f:
                history = json.load(f)
        else:
            history = []

        history.append(record)

        temporary_file = HISTORY_FILE.with_suffix(".tmp")

        with temporary_file.open(
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                history,
                f,
                indent=4,
                ensure_ascii=False
            )

        temporary_file.replace(HISTORY_FILE)

    return record
