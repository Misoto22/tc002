"""Keep tests away from the real ~/.cache/tc002 state files."""

import pytest

from tc002.integrations import statusline
from tc002.runtime import hold, sessions
from tc002.usage import claude, claude_login, limits


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(hold, "PATH", tmp_path / "hold.json")
    monkeypatch.setattr(sessions, "DIR", tmp_path / "sessions")
    monkeypatch.setattr(limits, "PATH", tmp_path / "claude-limits.json")
    monkeypatch.setattr(statusline, "SAVED", tmp_path / "statusline.json")
    monkeypatch.setattr(claude, "PROJECTS", str(tmp_path / "claude-projects"))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex"))
    # never read the real Claude login or call Anthropic from a test
    monkeypatch.setattr(claude_login, "_logins", lambda: iter(()))
