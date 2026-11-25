"""The focus timer's state: started by the UI or `tc002 focus start`, read by its screen.

A file, like the other hand-offs between commands and the service, so starting a timer
never needs the service to be listening.
"""

import json
import time

from .. import paths

PATH = paths.CACHE_DIR / "focus.json"


def start(minutes, break_minutes, path=None, now=None):
    path = path or PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "started": time.time() if now is None else now,
        "minutes": minutes,
        "break": break_minutes,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc))
    tmp.replace(path)
    return doc


def stop(path=None):
    (path or PATH).unlink(missing_ok=True)


def current(path=None, now=None):
    """("focus" | "break", seconds left) while a timer runs, else None (and tidies up)."""
    try:
        doc = json.loads((path or PATH).read_text())
        started, focus_s, break_s = doc["started"], doc["minutes"] * 60, doc["break"] * 60
    except OSError, ValueError, KeyError, TypeError:
        return None
    gone = (time.time() if now is None else now) - started
    if gone < focus_s:
        return "focus", focus_s - gone
    if gone < focus_s + break_s:
        return "break", focus_s + break_s - gone
    stop(path)
    return None
