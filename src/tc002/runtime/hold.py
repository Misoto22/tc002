"""A short-lived "hands off the screen" flag, set by the UI's live preview.

While it is active the rotation driver does not switch screens, so a setting being
previewed on the clock is not replaced by the next slot. It expires on its own, so a
closed browser tab can never freeze the rotation for long.
"""

import json
import os
import time
from pathlib import Path

PATH = Path(os.environ.get("TC002_HOLD_FILE", "~/.cache/tc002/hold.json")).expanduser()
MAX_SECONDS = 300


def hold(seconds=120, path=None, now=None):
    path = path or PATH
    now = time.time() if now is None else now
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"until": now + min(seconds, MAX_SECONDS)}))
    tmp.replace(path)


def release(path=None):
    (path or PATH).unlink(missing_ok=True)


def active(path=None, now=None):
    """Seconds left on the hold, or 0 when there is none (or the file is unreadable)."""
    now = time.time() if now is None else now
    try:
        until = float(json.loads((path or PATH).read_text())["until"])
    except OSError, ValueError, KeyError, TypeError:
        return 0
    return max(0, until - now)
