"""What the Integrations page can do to this Mac: connect Claude Code, run the service
(both through the application layer), show its log, reveal a file in Finder. Each action
is one of a fixed set."""

import subprocess
from collections import deque

from ..integrations import launchd

LOG_LINES = 200


def _installed(done):
    return {"installed": done["installed"], "service": done["status"]}


# the Integrations page's buttons: action -> App method
ACTIONS = {
    "connect-claude": lambda app: app.connect_claude(),
    "disconnect-claude": lambda app: app.disconnect_claude(),
    "install-service": lambda app: _installed(app.service_install()),
    "restart-service": lambda app: app.service_restart(),
}


def run(app, action):
    if action not in ACTIONS:
        raise KeyError(action)
    return ACTIONS[action](app) or {}


def log_tail(lines=LOG_LINES):
    try:
        with launchd.LOG.open(encoding="utf-8", errors="replace") as f:
            return "".join(deque(f, maxlen=lines))
    except FileNotFoundError:
        return ""


def reveal(path):
    """Show a file tc002 owns in Finder; refuses anything else."""
    subprocess.run(["open", "-R", str(path)], check=True, timeout=10)
