"""Put `tc002 statusline` in front of Claude Code's status line, and take it out again.

Claude Code only hands plan limits to the status line command. tc002 becomes that
command, saves the limits (usage/limits.py), then runs the command you had before with
the same input and prints its output, so the status line you see does not change. The
previous command is kept in ~/.config/tc002/statusline.json, never re-quoted, and put
back by uninstall.
"""

import contextlib
import json
import os
import subprocess
from pathlib import Path

from .. import paths
from ..usage import limits
from .claude_hooks import SETTINGS, _load, _save

SAVED = Path(os.environ.get("TC002_STATUSLINE_FILE", paths.STATE_DIR / "statusline.json"))
TIMEOUT = 5  # Claude Code waits on the status line; never hold it up for long


def command(executable):
    return f"{executable} statusline"


def _ours(entry, executable):
    cmd = (entry or {}).get("command", "")
    return cmd == command(executable) or cmd.endswith("/tc002 statusline")


def install(executable, path=SETTINGS, saved=None):
    """Wrap the current status line; returns False when it was already wrapped."""
    saved = saved or SAVED
    data = _load(path)
    current = data.get("statusLine")
    if _ours(current, executable):
        return False
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_text(json.dumps({"previous": current}))
    data["statusLine"] = {**(current or {}), "type": "command", "command": command(executable)}
    _save(path, data)
    return True


def uninstall(executable, path=SETTINGS, saved=None):
    """Put the previous status line back; returns False when tc002 was not in front."""
    saved = saved or SAVED
    data = _load(path)
    if not _ours(data.get("statusLine"), executable):
        return False
    previous = _previous(saved)
    if previous:
        data["statusLine"] = previous
    else:
        data.pop("statusLine", None)
    _save(path, data)
    saved.unlink(missing_ok=True)
    return True


def status(executable, path=SETTINGS):
    return _ours(_load(path).get("statusLine"), executable)


def _previous(saved):
    try:
        return json.loads(saved.read_text()).get("previous")
    except OSError, ValueError, AttributeError:
        return None


def run(raw, saved=None):
    """Handle one status line call: save the limits, then return what to print."""
    saved = saved or SAVED
    with contextlib.suppress(ValueError):  # not JSON: still show the user's own status line
        limits.record(json.loads(raw or b"{}"))
    previous = _previous(saved) or {}
    cmd = previous.get("command") if previous.get("type", "command") == "command" else None
    if not cmd:
        return _summary()
    try:
        done = subprocess.run(cmd, shell=True, input=raw, capture_output=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return b""
    return done.stdout


def _summary():
    """A one-line status line for people who had none: the two limits, when known."""
    now = limits.latest()
    parts = [
        f"{label} {now[key]:.0f}%"
        for label, key in (("5h", "limit_5h"), ("7d", "limit_week"))
        if now.get(key) is not None
    ]
    return (" · ".join(parts) + "\n").encode() if parts else b""
