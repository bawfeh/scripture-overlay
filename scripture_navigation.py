import json
import threading

from config import NAV_FILE

_lock = threading.RLock()


def _read():
    if not NAV_FILE.exists():
        return {"entries": [], "position": -1}

    return json.loads(NAV_FILE.read_text(encoding="utf-8"))


def _write(state):
    NAV_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = NAV_FILE.with_suffix(".tmp")
    temp.write_text(
        json.dumps(state, indent=2),
        encoding="utf-8"
    )
    temp.replace(NAV_FILE)


def status():
    with _lock:
        state = _read()
        pos = state["position"]
        entries = state["entries"]

        return {
            "position": pos,
            "total": len(entries),
            "can_back": pos > 0,
            "can_forward": 0 <= pos < len(entries) - 1,
            "current": entries[pos] if 0 <= pos < len(entries) else None
        }


def record(provider, reference, version):
    entry = {
        "provider": provider,
        "reference": reference,
        "version": version
    }

    with _lock:
        state = _read()
        entries = state["entries"]
        pos = state["position"]

        if pos >= 0 and entries[pos] == entry:
            return status()

        # A new selection invalidates forward history.
        state["entries"] = entries[:pos + 1] + [entry]
        state["position"] = len(state["entries"]) - 1

        _write(state)
        return status()


def target(direction):
    if direction not in (-1, 1):
        raise ValueError("Invalid navigation direction")

    with _lock:
        state = _read()
        pos = state["position"] + direction

        if not 0 <= pos < len(state["entries"]):
            return None

        return state["entries"][pos]


def advance(direction):
    """Commit navigation after Scripture restoration succeeds."""
    with _lock:
        state = _read()
        pos = state["position"] + direction

        if not 0 <= pos < len(state["entries"]):
            return None

        state["position"] = pos
        _write(state)
        return status()
