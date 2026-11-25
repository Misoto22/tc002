"""CLI command handlers that touch only this Mac."""

from types import SimpleNamespace

from tc002 import app as app_layer
from tc002.app import reads
from tc002.cli import commands


def test_doctor_without_any_claude_session_says_none_yet(monkeypatch, capsys):
    monkeypatch.setattr(reads.launchd, "status", lambda: "not installed")
    monkeypatch.setattr(reads.claude_hooks, "status", lambda exe: {"Stop": True})
    monkeypatch.setattr(reads.statusline, "status", lambda exe: True)
    monkeypatch.setattr(reads, "executable", lambda: "/bin/tc002")
    monkeypatch.setattr(reads.sessions, "load", list)  # a fresh install: no sessions
    commands.doctor(None, SimpleNamespace(app=app_layer.App()))  # no clock configured
    assert "sessions: none yet" in capsys.readouterr().out
