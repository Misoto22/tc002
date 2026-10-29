"""Per-session states recorded by `tc002 hook`, and the Sessions screen that shows them."""

import os

import pytest

from tc002 import cli
from tc002.render.canvas import rgb
from tc002.render.palette import LED
from tc002.runtime import sessions
from tc002.screens import claude

T0 = 1_800_000_000.0


def hook(tmp_path, event, sid="s1", now=T0, **extra):
    payload = {"hook_event_name": event, "session_id": sid, "cwd": "/Users/me/code/kura"}
    transcript = tmp_path / f"{sid}.jsonl"
    transcript.touch()
    os.utime(transcript, (now, now))
    payload["transcript_path"] = str(transcript)
    return sessions.record_hook({**payload, **extra}, tmp_path / "s", now)


def load(tmp_path, now):
    return sessions.load(tmp_path / "s", now)


def test_a_turn_goes_working_then_done(tmp_path):
    hook(tmp_path, "SessionStart")
    hook(tmp_path, "UserPromptSubmit", now=T0 + 1)
    (s,) = load(tmp_path, T0 + 2)
    assert (s.project, s.state, s.since) == ("kura", "working", T0 + 1)
    hook(tmp_path, "Stop", now=T0 + 30)
    assert load(tmp_path, T0 + 31)[0].state == "done"


def test_permission_notice_waits_until_the_transcript_moves(tmp_path):
    hook(tmp_path, "UserPromptSubmit")
    hook(tmp_path, "Notification", now=T0 + 5, message="Claude needs permission to use Bash")
    (s,) = load(tmp_path, T0 + 60)
    assert s.state == "waiting" and "permission" in s.message
    os.utime(tmp_path / "s1.jsonl", (T0 + 70, T0 + 70))  # you answered; Claude carries on
    assert load(tmp_path, T0 + 71)[0].state == "working"


def test_idle_notice_is_not_a_question(tmp_path):
    hook(tmp_path, "Stop")
    hook(tmp_path, "Notification", now=T0 + 60, message="Claude is waiting for your input")
    assert load(tmp_path, T0 + 61)[0].state == "done"


def test_done_goes_idle_after_an_hour_and_end_forgets(tmp_path):
    hook(tmp_path, "Stop")
    assert load(tmp_path, T0 + sessions.DONE_UNREAD + 1)[0].state == "idle"
    hook(tmp_path, "SessionEnd", now=T0 + 2)
    assert load(tmp_path, T0 + 3) == []


def test_old_sessions_are_forgotten(tmp_path):
    hook(tmp_path, "UserPromptSubmit")
    assert load(tmp_path, T0 + sessions.FORGET + 1) == []
    assert not list((tmp_path / "s").glob("*.json"))


@pytest.mark.parametrize("sid", ["../../etc/passwd", "", None, "a" * 81])
def test_unsafe_session_ids_are_refused(tmp_path, sid):
    with pytest.raises(ValueError):
        sessions.record_hook({"hook_event_name": "Stop", "session_id": sid}, tmp_path)


def test_hook_command_reads_stdin_and_never_fails(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO('{"hook_event_name": "Stop",'))
    assert cli.main(["hook"]) == 0  # half a JSON document: reported, not raised
    assert "could not record hook" in capsys.readouterr().err


def test_screen_counts_states_and_waiting_takes_over(tmp_path):
    hook(tmp_path, "UserPromptSubmit", sid="a")
    hook(tmp_path, "Stop", sid="b")
    hook(tmp_path, "Notification", sid="c", now=T0 + 1, message="needs permission")
    screen = claude.ClaudeScreen(str(tmp_path / "none"), clock=lambda: T0 + 30, root=tmp_path / "s")
    assert screen.sample() == claude.State(1, 1, 1, ("wait", "kura"))


def test_finished_session_flashes_done_briefly(tmp_path):
    hook(tmp_path, "Stop")
    screen = claude.ClaudeScreen(str(tmp_path / "none"), clock=lambda: T0 + 2, root=tmp_path / "s")
    assert screen.sample().alert == ("done", "kura")
    late = claude.ClaudeScreen(str(tmp_path / "none"), clock=lambda: T0 + 60, root=tmp_path / "s")
    assert late.sample() == claude.State(0, 0, 1)


def test_transcripts_without_hooks_still_count_as_running(tmp_path):
    proj = tmp_path / "projects" / "p"
    proj.mkdir(parents=True)
    (proj / "x.jsonl").write_text("{}")
    screen = claude.ClaudeScreen(str(tmp_path / "projects"), root=tmp_path / "s")
    assert screen.sample().working == 1


def test_zero_columns_are_grey_and_ask_blinks():
    anim = claude.ClaudeScreen().render(claude.State(0, 2, 0))
    first, blink = anim.frames[0], anim.frames[5]
    assert rgb(LED["amber"]) in first.px and rgb(LED["amber"]) not in blink.px
    assert rgb(LED["sky"]) not in first.px and rgb(LED["green"]) not in first.px
