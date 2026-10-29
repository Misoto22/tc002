"""Hooks into the host: launchd (background service) and Claude Code (hook events)."""

import shutil


def executable():
    """Absolute path of the installed `tc002` command, which launchd and hooks invoke."""
    path = shutil.which("tc002")
    if path is None:
        raise RuntimeError("`tc002` is not on PATH; run `uv tool install .` in the clone first")
    return path
