"""CLI command handlers that touch only this Mac."""

from types import SimpleNamespace

from tc002 import app as app_layer
from tc002.cli import commands


def test_doctor_without_any_claude_session_says_none_yet(monkeypatch, capsys):
    monkeypatch.setattr(app_layer.launchd, "status", lambda: "not installed")
    monkeypatch.setattr(app_layer.claude_hooks, "status", lambda exe: {"Stop": True})
    monkeypatch.setattr(app_layer.statusline, "status", lambda exe: True)
    monkeypatch.setattr(app_layer, "executable", lambda: "/bin/tc002")
    monkeypatch.setattr(app_layer.sessions, "load", list)  # a fresh install: no sessions
    commands.doctor(None, SimpleNamespace(app=app_layer.App()))  # no clock configured
    assert "sessions: none yet" in capsys.readouterr().out
