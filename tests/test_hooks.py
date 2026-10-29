"""Claude Code hook installer against a temporary settings.json."""

import json

from tc002.integrations import claude_hooks

EXE = "/Users/me/.local/bin/tc002"
OTHER = {"type": "command", "command": "/Users/me/.claude/luvus-agent-hook.sh"}


def settings(tmp_path, data):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(data))
    return path


def commands(path, event):
    hooks = json.loads(path.read_text()).get("hooks", {})
    return [h["command"] for e in hooks.get(event, []) for h in e["hooks"]]


def test_install_adds_hooks_beside_existing_ones_and_backs_up(tmp_path):
    path = settings(tmp_path, {"model": "x", "hooks": {"Stop": [{"hooks": [OTHER]}]}})
    assert claude_hooks.install(EXE, path) == ["Stop", "Notification", "UserPromptSubmit"]
    assert commands(path, "Stop") == [OTHER["command"], claude_hooks.command(EXE, "done")]
    assert commands(path, "Notification") == [claude_hooks.command(EXE, "wait")]
    assert json.loads(path.read_text())["model"] == "x"
    assert (tmp_path / "settings.json.bak-tc002").exists()


def test_install_is_idempotent_and_refreshes_a_moved_executable(tmp_path):
    path = settings(tmp_path, {})
    claude_hooks.install(EXE, path)
    assert claude_hooks.install(EXE, path) == []
    claude_hooks.install("/opt/tc002", path)
    assert commands(path, "Stop") == [claude_hooks.command("/opt/tc002", "done")]


def test_uninstall_removes_only_ours(tmp_path):
    path = settings(tmp_path, {"hooks": {"Stop": [{"hooks": [OTHER]}]}})
    claude_hooks.install(EXE, path)
    assert set(claude_hooks.uninstall(EXE, path)) == {"Stop", "Notification", "UserPromptSubmit"}
    assert commands(path, "Stop") == [OTHER["command"]]
    assert "Notification" not in json.loads(path.read_text())["hooks"]
    assert claude_hooks.status(EXE, path) == dict.fromkeys(claude_hooks.EVENTS, False)


def test_missing_settings_file_is_created(tmp_path):
    path = tmp_path / "nested" / "settings.json"
    claude_hooks.install(EXE, path)
    assert all(claude_hooks.status(EXE, path).values())
