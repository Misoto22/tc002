"""Plan limits: saved from Claude Code's status line, read from Codex logs, drawn on the clock."""

import json

from tc002.integrations import statusline
from tc002.render.canvas import rgb
from tc002.render.palette import LED
from tc002.screens import usage
from tc002.usage import limits

EXE = "/Users/me/.local/bin/tc002"
STATUS = {
    "rate_limits": {
        "five_hour": {"used_percentage": 62.4, "resets_at": "2027-01-15T10:00:00Z"},
        "seven_day": {"used_percentage": 38, "resets_at": 1_900_000_000},
    }
}


def test_status_line_limits_are_saved_and_read_back(tmp_path):
    path = tmp_path / "l.json"
    assert limits.record(STATUS, path, now=1_800_000_000)
    got = limits.latest(path, now=1_800_000_100)
    assert got["limit_5h"] == 62.4 and got["limit_week"] == 38.0
    assert got["reset_week"] == 1_900_000_000


def test_a_window_that_has_reset_reads_zero(tmp_path):
    path = tmp_path / "l.json"
    limits.record(STATUS, path, now=1_800_000_000)
    assert limits.latest(path, now=1_950_000_000)["limit_week"] == 0.0


def test_inputs_without_limits_save_nothing(tmp_path):
    assert not limits.record({"model": {"id": "x"}}, tmp_path / "l.json")
    assert limits.latest(tmp_path / "l.json") == {}


def _settings(tmp_path, data):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(data))
    return path


def test_wrapper_keeps_the_previous_status_line_and_restores_it(tmp_path):
    before = {"type": "command", "command": "bash ~/.claude/statusline.sh", "padding": 0}
    path = _settings(tmp_path, {"statusLine": before})
    saved = tmp_path / "saved.json"
    assert statusline.install(EXE, path, saved)
    assert not statusline.install(EXE, path, saved)  # already in front
    now = json.loads(path.read_text())["statusLine"]
    assert now["command"] == f"{EXE} statusline" and now["padding"] == 0
    assert statusline.uninstall(EXE, path, saved)
    assert json.loads(path.read_text())["statusLine"] == before


def test_wrapper_runs_the_previous_command_with_the_same_input(tmp_path):
    saved = tmp_path / "saved.json"
    saved.write_text(json.dumps({"previous": {"type": "command", "command": "cat"}}))
    raw = json.dumps(STATUS).encode()
    assert statusline.run(raw, saved) == raw
    assert limits.latest()["limit_5h"] == 62.4


def test_without_a_previous_status_line_it_prints_the_limits(tmp_path):
    out = statusline.run(json.dumps(STATUS).encode(), tmp_path / "none.json")
    assert out.startswith(b"5h 62%")


def test_usage_screen_marks_unknown_and_high_usage():
    state = usage.State((usage.Row("claude", 85, 40), usage.Row("codex", None, None)))
    still = usage.frame(state)
    assert rgb(LED["amber"]) in still.px  # 85 % is a warning
    assert rgb(LED["teal"]) not in still.px  # Codex unknown: grey mark, empty bar
    assert len(usage.render(state).frames) == usage.FILL_FRAMES


def test_usage_screen_blinks_when_nearly_out():
    state = usage.State((usage.Row("claude", 97, 40), usage.Row("codex", 10, 10)))
    assert len(usage.render(state).frames) == usage.FILL_FRAMES + 8
