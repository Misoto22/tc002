"""Claude Code hook events, handed from `tc002 event` to the running watcher via a file.

Hooks must return instantly and must never touch the network, so they only record
the event; the watcher's Claude screen picks it up on its next sample.
"""

import json
import os
import time
from pathlib import Path

PATH = Path(os.environ.get("TC002_EVENT_FILE", "~/.cache/tc002/event.json")).expanduser()
KINDS = ("done", "wait", "clear")


def record(kind, path=PATH, now=None):
    """Atomically replace the last event; last writer wins across sessions."""
    if kind not in KINDS:
        raise ValueError(f"unknown event {kind!r}; expected one of {KINDS}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"kind": kind, "time": time.time() if now is None else now}))
    tmp.replace(path)


def latest(path=PATH):
    """(kind, unix time) of the last event, or (None, 0) when there is none or it is unreadable."""
    try:
        data = json.loads(path.read_text())
        return data["kind"], float(data["time"])
    except OSError, ValueError, KeyError, TypeError:
        return None, 0.0
