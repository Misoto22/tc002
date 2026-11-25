"""Showing a file tc002 owns in the Finder."""

import subprocess


def reveal(path):
    """Select `path` in a Finder window (`open -R`)."""
    subprocess.run(["open", "-R", str(path)], check=True, timeout=10)
