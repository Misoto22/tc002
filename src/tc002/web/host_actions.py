"""What the Integrations page can do to this Mac: connect Claude Code, run the service,
show its log, reveal a file in Finder. Each action is one of a fixed set."""

import subprocess
from collections import deque

from ..integrations import claude_hooks, executable, launchd, statusline

LOG_LINES = 200


def _connect():
    exe = executable()
    return {"hooks": claude_hooks.install(exe), "statusline": statusline.install(exe)}


def _disconnect():
    exe = executable()
    return {"hooks": claude_hooks.uninstall(exe), "statusline": statusline.uninstall(exe)}


ACTIONS = {
    "connect-claude": _connect,
    "disconnect-claude": _disconnect,
    "install-service": lambda: launchd.install(executable()) or {"service": launchd.status()},
    "restart-service": lambda: {"restarted": launchd.restart(), "service": launchd.status()},
}


def run(action):
    if action not in ACTIONS:
        raise KeyError(action)
    return ACTIONS[action]() or {}


def log_tail(lines=LOG_LINES):
    try:
        with launchd.LOG.open(encoding="utf-8", errors="replace") as f:
            return "".join(deque(f, maxlen=lines))
    except FileNotFoundError:
        return ""


def reveal(path):
    """Show a file tc002 owns in Finder; refuses anything else."""
    subprocess.run(["open", "-R", str(path)], check=True, timeout=10)
