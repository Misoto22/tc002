"""Rendering and sampling of every screen."""

import pytest

from tc002 import builtins
from tc002.render import font
from tc002.render.anim import MAX_FRAMES
from tc002.render.canvas import WIDTH, Canvas, rgb
from tc002.screens import builtin_previews, claude, message, sysmon, usage

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
        claude.ClaudeScreen().render(claude.State(3, 1, 2)),
        claude.ClaudeScreen().render(claude.State(0, 0, 0)),
        claude.ClaudeScreen().render(claude.State(1, 1, 0, ("wait", "a-very-long-project"))),
        claude.ClaudeScreen().render(claude.State(0, 0, 1, ("done", "kura"))),
        usage.render(usage.State((usage.Row("claude", 97, 70), usage.Row("codex", None, 5)))),
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


@pytest.mark.parametrize("key", sorted(builtins.CATALOGUE))
def test_every_builtin_has_a_preview_that_fits(key):
    anim = builtin_previews.render(key)
    assert lit(anim.frames[0]) > 0
    anim.payload()


def test_chinese_messages_use_the_cjk_font_and_fit():
    from tc002.render import cjk

    assert font.for_text("构建完成") is cjk.FONT and font.for_text("BUILD OK") is font.BIG
    (anim,) = message.text_animation("构建完成", "green")  # four characters fit without scrolling
    assert lit(anim.frames[-1]) > 40
    assert lit(message.alert_animation("完成", "done").frames[0]) > 0


def test_unknown_characters_fall_back_instead_of_failing():
    anims = message.text_animation("emoji 🙂 here", "white")
    assert all(len(a.frames) <= MAX_FRAMES for a in anims)
