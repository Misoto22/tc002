"""How fresh each screen's data is, kept by the service and read by the UI.

The service records every sample (ok, or the error) per screen and writes the lot to
~/.cache/tc002/screens.json, so the settings UI can say "updated 5 s ago" or "no data for
12 min: <reason>" without asking the service anything.
"""

import json
import threading
import time
from pathlib import Path

from .. import paths
from ..screens import stale

PATH = paths.CACHE_DIR / "screens.json"


class Freshness:
    """Thread-safe record of the last good sample and last error of every screen."""

    def __init__(self, path=None, clock=time.time):
        self.path, self.clock = Path(path or PATH), clock
        self._lock = threading.Lock()
        self._screens = {}  # app -> {"ok_at": t or None, "state": last good state, "error": str}

    def ok(self, app, state):
        with self._lock:
            self._screens[app] = {"ok_at": self.clock(), "state": state, "error": None}
            self._write()

    def failed(self, app, error):
        with self._lock:
            entry = self._screens.setdefault(app, {"ok_at": None, "state": None, "error": None})
            entry["error"] = str(error)[:200]
            self._write()

    def last(self, app):
        """(last good state or None, seconds since it or None)."""
        with self._lock:
            entry = self._screens.get(app, {})
            ok_at = entry.get("ok_at")
            return entry.get("state"), None if ok_at is None else self.clock() - ok_at

    def _write(self):
        doc = {app: {"okAt": e["ok_at"], "error": e["error"]} for app, e in self._screens.items()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc))
        tmp.replace(self.path)


def read(path=None, now=None):
    """{app: {"age": seconds since the last good sample or None, "error": str or None,
    "stale": bool}} from the service's file; {} when the service has not written one."""
    try:
        doc = json.loads(Path(path or PATH).read_text())
    except OSError, ValueError:
        return {}
    now = time.time() if now is None else now
    out = {}
    for app, entry in doc.items():
        age = None if entry.get("okAt") is None else round(now - entry["okAt"])
        failing = bool(entry.get("error")) and (age is None or age >= stale.STALE_AFTER)
        out[app] = {"age": age, "error": entry.get("error"), "stale": failing}
    return out
