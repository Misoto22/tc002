"""Gemini plan limits, asked of Antigravity's own language server on this Mac.

While Antigravity runs, its language server listens on 127.0.0.1 and writes the port and
a per-run CSRF token to ~/.gemini/antigravity/daemon/hub_<port>.json. Its GetUserStatus
reply lists every model with `quotaInfo: {remainingFraction, resetTime}`; the Gemini
models share one allowance, so the most-used of them is the one reported.

Only one window comes back: the one that binds now. When it refills within five hours it
is the 5-hour allowance; when it refills later, the weekly cap is what binds. Readings
are saved (same shape as limits.py) so the screen keeps the last known numbers while
Antigravity is closed, and a window whose reset time has passed reads 0 %.

The token is read from the port file on each ask, sent only to 127.0.0.1, and never
logged or saved. Nothing here leaves this Mac.
"""

import glob
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from .. import paths
from . import FIVE_HOURS, Usage, limits

PATH = Path(os.environ.get("TC002_GEMINI_LIMITS_FILE", paths.CACHE_DIR / "gemini-limits.json"))
STATUS = "/exa.language_server_pb.LanguageServerService/GetUserStatus"
REFRESH = 60  # seconds between asks; the server is local, so this only bounds the work
TIMEOUT = 3
GRACE = 15 * 60  # a 5-hour window's reset can sit a little past five hours from now


def _servers(daemon):
    """(port, csrf token) of each language server that left a port file, newest first."""
    files = sorted(glob.glob(os.path.join(daemon, "hub_*.json")), key=os.path.getmtime)
    for path in reversed(files):
        try:
            info = json.loads(Path(path).read_text())
            port, token = int(info["httpPort"]), info["csrfToken"]
        except OSError, ValueError, KeyError, TypeError:
            continue
        if isinstance(token, str) and token:
            yield port, token


def fetch(port, token):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{STATUS}",
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "Connect-Protocol-Version": "1",
            "X-Codeium-Csrf-Token": token,
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def _epoch(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except AttributeError, ValueError:
        return None


def quota(reply):
    """(% used, reset time) of the Gemini allowance in a GetUserStatus reply, or None."""
    try:
        configs = reply["userStatus"]["cascadeModelConfigData"]["clientModelConfigs"]
    except KeyError, TypeError:
        return None
    worst = None
    for config in configs if isinstance(configs, list) else []:
        info = (config or {}).get("quotaInfo") or {}
        left = info.get("remainingFraction", 0 if "resetTime" in info else None)
        if "gemini" not in str(config.get("label", "")).lower():
            continue  # Claude and GPT models in Antigravity draw on their own allowance
        if not isinstance(left, int | float):
            continue
        used = round(max(0.0, min(1.0, 1 - left)) * 100, 1)
        if worst is None or used > worst[0]:
            worst = (used, _epoch(info.get("resetTime")))
    return worst


def window(resets, now):
    """Which allowance a reading belongs to, judged by when it refills."""
    if resets is None or resets <= now + FIVE_HOURS + GRACE:
        return "five_hour"
    return "seven_day"


def record(reading, path=None, now=None):
    """Save one reading into its window, keeping the other window's last known value."""
    now = time.time() if now is None else now
    used, resets = reading
    path = path or PATH
    try:
        saved = json.loads(path.read_text())
    except OSError, ValueError:
        saved = {}
    which = window(resets, now)
    if which == "seven_day":  # a weekly cap that binds leaves no 5-hour figure to trust
        saved.pop("five_hour", None)
    saved.update({"at": now, which: {"used": used, "resets_at": resets}})
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(saved))
    tmp.replace(path)


def refresh_if_due(now=None, path=None, daemon=None):
    """Ask Antigravity for fresh limits; returns "fresh", "saved", "not-running" or "failed"."""
    if limits.age(path or PATH, now) < REFRESH:
        return "fresh"
    for port, token in _servers(daemon or str(paths.ANTIGRAVITY_DAEMON)):
        try:
            reading = quota(fetch(port, token))
        except urllib.error.URLError, OSError, ValueError:
            continue  # a port file left by a server that has since exited
        if reading is None:
            return "failed"
        record(reading, path, now)
        return "saved"
    return "not-running"


class GeminiUsage:
    def __init__(self, daemon=None, path=None, clock=time.time):
        self.daemon, self.path, self.clock = daemon, path, clock

    def collect(self):
        now, path = self.clock(), self.path or PATH
        refresh_if_due(now, path, self.daemon)
        known = limits.latest(path, now)
        daemon = self.daemon or str(paths.ANTIGRAVITY_DAEMON)
        seen = known or glob.glob(os.path.join(daemon, "hub_*.json"))
        # Antigravity keeps no token log tc002 could add up, so only the limits are known.
        return Usage(0, 0, source="antigravity" if seen else "none", **known)
