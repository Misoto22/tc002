"""A screen whose data stops: the age shows, then NO DATA; the UI reads the same record."""

import threading

from tc002.render.palette import LED
from tc002.runtime import freshness, watcher
from tc002.screens import stale, sysmon

T0 = 1_800_000_000.0


class Recorder:
    def __init__(self):
        self.shown = []

    def show(self, app, anim):
        self.shown.append(anim)


class Flaky:
    """A screen that works until `broken` is set."""

    APP, TICK = "sys", 1
    broken = False

    def sample(self):
        if self.broken:
            raise OSError("iostat: command not found")
        return sysmon.State(40, 50, (40,) * 52)

    def render(self, state):
        return sysmon.SysScreen().render(state)


def run_once(screen, out, record):
    watcher.screen_loop(out, screen, threading.Event(), watcher.Attention(), True, record)


def test_age_labels_fit_the_small_font():
    assert [stale.age_label(s) for s in (45, 300, 7200)] == ["45S", "5M", "2H"]


def test_a_blip_keeps_the_picture_then_the_age_then_no_data(tmp_path):
    clock = [T0]
    record = freshness.Freshness(tmp_path / "s.json", clock=lambda: clock[0])
    screen, out = Flaky(), Recorder()
    run_once(screen, out, record)  # good sample
    screen.broken = True
    clock[0] += 5
    run_once(screen, out, record)
    assert len(out.shown) == 1  # a 5 s blip changes nothing
    clock[0] += stale.STALE_AFTER
    run_once(screen, out, record)
    aged = out.shown[-1]
    assert aged.key[0] == "stale" and any(p == LED["amber"] for p in aged.frames[0].px)
    clock[0] += stale.NO_DATA_AFTER
    run_once(screen, out, record)
    assert out.shown[-1].key[0] == "no-data"


def test_the_ui_reads_age_and_reason(tmp_path):
    path = tmp_path / "s.json"
    record = freshness.Freshness(path, clock=lambda: T0)
    record.ok("sys", "state")
    record.failed("sys", OSError("iostat missing"))
    got = freshness.read(path, now=T0 + 120)["sys"]
    assert got == {"age": 120, "error": "iostat missing", "stale": True}
    assert freshness.read(tmp_path / "none.json") == {}


def test_stale_pictures_fit_the_clock():
    stale.no_data("sys", 900).payload()
    stale.no_data("claude").payload()
    stale.mark(sysmon.SysScreen().render(sysmon.State(1, 2, (1,) * 52)), 75).payload()
