"""CLI command handlers that touch only this Mac."""

from types import SimpleNamespace

from tc002.cli import commands


def test_doctor_without_any_claude_session_says_none_yet(monkeypatch, capsys):
    monkeypatch.setattr(commands.launchd, "status", lambda: "not installed")
    monkeypatch.setattr(commands.claude_hooks, "status", lambda exe: {"Stop": True})
    monkeypatch.setattr(commands.statusline, "status", lambda exe: True)
    monkeypatch.setattr(commands, "executable", lambda: "/bin/tc002")
    monkeypatch.setattr(commands.sessions, "load", list)  # a fresh install: no sessions
    ctx = SimpleNamespace(settings=SimpleNamespace(source="tc002.toml"), device=None)
    commands.doctor(None, ctx)
    assert "sessions: none yet" in capsys.readouterr().out
