"""Rendering and sampling of every screen."""

import os
import time

import pytest

from tc002.render import font
from tc002.render.anim import MAX_FRAMES
from tc002.render.canvas import WIDTH, Canvas, rgb
from tc002.runtime import events
from tc002.screens import claude, message, sysmon

VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                     7185.
Pages active:                                 100000.
Pages wired down:                              50000.
Pages occupied by compressor:                  50000.
"""
IOSTAT = """      cpu    load average
 us sy id   1m   5m   15m
 32 18 50  130.30 65.33 35.13
 24 13 62  125.15 65.34 35.31
"""


def lit(canvas):
    return sum(1 for p in canvas.px if p)


def test_canvas_clips_off_screen_writes():
    c = Canvas()
    c.set(0, 0, "#FF0000")
    c.set(99, 99, "#FFFFFF")
    assert c.get(0, 0) == 0xFF0000 and c.get(99, 99) == 0 and lit(c) == 1


def test_text_width_and_unknown_glyph_fallback():
    assert font.text_width(font.BIG, "A") == 5
    assert font.text_width(font.BIG, "AA") == 11
    assert font.glyph(font.BIG, "é") == font.glyph(font.BIG, "?")
    assert font.glyph(font.SMALL, "a") == font.glyph(font.SMALL, "A")


def _transcripts(tmp_path, subagent=True):
    proj = tmp_path / "proj"
    (proj / "s1" / "subagents").mkdir(parents=True)
    (proj / "s1.jsonl").write_text("{}")
    if subagent:
        (proj / "s1" / "subagents" / "a.jsonl").write_text("{}")
    stale = proj / "s2.jsonl"
    stale.write_text("{}")
    old = time.time() - 3600
    os.utime(stale, (old, old))
    return str(tmp_path)


def test_claude_counts_recent_sessions_and_subagents(tmp_path):
    screen = claude.ClaudeScreen(_transcripts(tmp_path), cpu=lambda: 50.0)
    assert screen.sample() == claude.State(1, 1, True)


def test_claude_busy_holds_through_short_cpu_dips(tmp_path):
    now = [1000.0]
    cpu = [50.0]
    screen = claude.ClaudeScreen(_transcripts(tmp_path), cpu=lambda: cpu[0], clock=lambda: now[0])
    # transcripts were written "now" in wall time; keep the fake clock close to it
    now[0] = time.time()
    assert screen.sample().busy
    cpu[0], now[0] = 0.0, now[0] + claude.BUSY_HOLD - 1
    assert screen.sample().busy  # tool wait: still busy
    now[0] += 2
    assert not screen.sample().busy


def test_claude_not_busy_without_sessions(tmp_path):
    screen = claude.ClaudeScreen(str(tmp_path), cpu=lambda: 99.0)
    assert screen.sample() == claude.State(0, 0, False)


def test_claude_busy_animation_spins_and_shows_satellites():
    anim = claude.ClaudeScreen().render(claude.State(3, 2, True))
    assert anim.key == claude.State(3, 2, True)
    loop = anim.frames[:16]  # one turn of the spin; it plays twice, then the stats card
    assert len({tuple(f.px) for f in loop}) == len(loop)  # every frame moves
    assert len(anim.frames) <= MAX_FRAMES
    assert all(rgb(claude.YELLOW) in f.px for f in loop)


def test_claude_off_has_no_activity_colours():
    anim = claude.ClaudeScreen().render(claude.State(0, 0, False))
    assert all(rgb(claude.GREEN) not in f.px for f in anim.frames[:24])


def test_mem_percent_from_vm_stat():
    used = (100000 + 50000 + 50000) * 16384
    assert sysmon.mem_percent(VM_STAT, used * 2) == 50


def test_mem_percent_rejects_unexpected_output():
    with pytest.raises(ValueError):
        sysmon.mem_percent("garbage", 1)


def test_cpu_percent_uses_last_iostat_line():
    assert sysmon.cpu_percent(IOSTAT) == 38


def test_cpu_percent_rejects_unexpected_output():
    with pytest.raises(ValueError):
        sysmon.cpu_percent("")


def test_sys_screen_scrolls_history():
    outputs = {"sysctl": "34359738368\n", "iostat": IOSTAT, "vm_stat": VM_STAT}
    screen = sysmon.SysScreen(run=lambda cmd: outputs[cmd[0]])
    first, second = screen.sample(), screen.sample()
    assert first.history[-1] == 38 and second.history[-2:] == (38, 38)
    assert len(second.history) == WIDTH


def test_sys_chart_height_follows_load():
    low = sysmon.SysScreen().render(sysmon.State(10, 10, (10,) * WIDTH)).frames[0]
    high = sysmon.SysScreen().render(sysmon.State(90, 10, (90,) * WIDTH)).frames[0]
    assert lit(high) > lit(low)


def test_short_text_sweeps_then_rests():
    (anim,) = message.text_animation("HI", "green")
    assert anim.delays()[-1] > anim.delays()[0]
    assert any(0xFFFFFF & p > rgb("#3EE08A") for f in anim.frames for p in f.px)


def test_long_text_scrolls_fully_across_in_device_sized_segments():
    text = "CLAUDE FINISHED THE BUILD"
    segments = message.text_animation(text, "white")
    frames = [f for seg in segments for f in seg.frames]
    assert len(segments) > 1  # more frames than one GIF may hold
    assert all(len(seg.frames) <= MAX_FRAMES for seg in segments)
    assert lit(frames[0]) == 0 and lit(frames[-1]) == 0


@pytest.mark.parametrize(
    "anim",
    [
        claude.ClaudeScreen().render(claude.State(3, 6, True)),
        claude.ClaudeScreen().render(claude.State(2, 0, False)),
        claude.ClaudeScreen().render(claude.State(0, 0, False)),
        sysmon.SysScreen().render(sysmon.State(99, 99, (99,) * WIDTH)),
        message.alert_animation("WAIT", "wait"),
        *message.text_animation("HI HENRY", "green"),
        *message.text_animation("A" * message.MAX_CHARS, "cyan"),
    ],
)
def test_every_animation_fits_the_firmware_gif_limits(anim):
    anim.payload()  # raises when over 50 frames or 60 KB


def test_alert_lights_chase_and_loop_seamlessly():
    frames = message.alert_animation("DONE", "done").frames
    assert frames[0].px != frames[1].px
    # border pattern advances 1 px per frame over a 6 px period: frame 6 would equal frame 0
    assert len(frames) == 6


def _hooked(tmp_path, clock, cpu=lambda: 0.0):
    event_file = tmp_path / "event.json"
    screen = claude.ClaudeScreen(
        _transcripts(tmp_path), cpu=cpu, clock=lambda: clock[0], event_path=event_file
    )
    return screen, event_file


def test_done_event_shows_then_expires(tmp_path):
    clock = [time.time()]
    screen, path = _hooked(tmp_path, clock)
    events.record("done", path, now=clock[0])
    assert screen.sample().alert == "done"
    clock[0] += claude.DONE_SECONDS + 1
    assert screen.sample().alert is None


def test_wait_event_clears_when_claude_resumes(tmp_path):
    clock, cpu = [time.time()], [0.0]
    screen, path = _hooked(tmp_path, clock, cpu=lambda: cpu[0])
    events.record("wait", path, now=clock[0])
    assert screen.sample().alert == "wait"
    clock[0] += 60
    assert screen.sample().alert == "wait"  # still unanswered a minute later
    cpu[0] = 50.0
    assert screen.sample().alert is None


def test_clear_event_and_missing_file_mean_no_alert(tmp_path):
    clock = [time.time()]
    screen, path = _hooked(tmp_path, clock)
    assert screen.sample().alert is None
    events.record("wait", path, now=clock[0])
    events.record("clear", path, now=clock[0])
    assert screen.sample().alert is None


def test_alert_state_renders_as_alert_animation():
    anim = claude.ClaudeScreen().render(claude.State(1, 0, False, "wait"))
    assert anim.key.alert == "wait" and len(anim.frames) == 6


def test_corrupt_event_file_is_ignored(tmp_path):
    path = tmp_path / "event.json"
    path.write_text("{not json")
    assert events.latest(path) == (None, 0.0)


def test_unknown_event_kind_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        events.record("boom", tmp_path / "e.json")
