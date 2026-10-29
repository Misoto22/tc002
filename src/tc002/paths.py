"""Where tc002 and the tools it reads keep their files: the one owner of every path.

Each can be moved with an environment variable, which is also how tests isolate them.
"""

import os
from pathlib import Path


def _dir(variable, default):
    return Path(os.environ.get(variable, default)).expanduser()


STATE_DIR = _dir("TC002_STATE_DIR", "~/.config/tc002")  # settings and saved layout
CACHE_DIR = _dir("TC002_CACHE_DIR", "~/.cache/tc002")  # state that can be rebuilt
CLAUDE_DIR = _dir("CLAUDE_CONFIG_DIR", "~/.claude")
CLAUDE_PROJECTS = CLAUDE_DIR / "projects"  # Claude Code's session transcripts
CODEX_HOME = _dir("CODEX_HOME", "~/.codex")
