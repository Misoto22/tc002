"""Night: the schedule, screen off/on against a fake clock, and the service pausing."""

import time

import pytest

from tc002 import config, config_writer, night
from tc002.device import DeviceError
from tc002.runtime.output import Output
from tc002.runtime.rotation import Attention, Rotation


def at(hh, mm):
    """An epoch time when this Mac's clock reads hh:mm (today, local time)."""
    t = time.localtime()
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, hh, mm, 0, 0, 0, -1))


class FakeClock:
    def __init__(self):
        self.pushes, self.switches, self.removed = [], [], []
        self.down = False

    def _check(self):
        if self.down:
            raise DeviceError("offline")

    def push(self, app, payload):
        self._check()
        self.pushes.append(app)

    def switch_custom(self, app):
        self._check()
        self.switches.append(app)

    def remove(self, app):
        self._check()
        self.removed.append(app)


def settings_with(night_table=None):
    return config.parse({"night": night_table} if night_table else {}, "test")


NIGHTLY = {"enable": True, "start": "23:00", "end": "07:00"}


@pytest.mark.parametrize(
    ("start", "end", "minute", "inside"),
    [
        ("22:00", "07:00", 23 * 60, True),  # wraps past midnight
        ("22:00", "07:00", 3 * 60, True),
        ("22:00", "07:00", 7 * 60, False),  # the end minute is light again
        ("22:00", "07:00", 12 * 60, False),
        ("01:00", "06:00", 2 * 60, True),
        ("01:00", "06:00", 0, False),
    ],
)
def test_in_window(start, end, minute, inside):
    schedule = {"enable": True, "start": start, "end": end}
    assert night.in_window(schedule, minute) is inside
    assert night.in_window({**schedule, "enable": False}, minute) is False


def test_validation_and_round_trip(tmp_path):
    assert night.validate(NIGHTLY) == []
    assert len(night.validate({"enable": "yes", "start": "25:00", "end": "7"})) == 3
    assert night.validate({"start": "07:00", "end": "07:00"})
    with pytest.raises(config.ConfigError):
        config.parse({"night": {"enable": True, "dim": 1}})

    path = tmp_path / "tc002.toml"
    config_writer.save(settings_with(NIGHTLY), path)
    assert config.load(path).night == NIGHTLY


def test_black_screen_is_one_black_frame():
    payload = night.black()
    assert payload["image"]  # a GIF the clock can show


def test_off_puts_the_black_screen_up_and_on_takes_it_down():
    clock = FakeClock()
    settings = settings_with()
    st = night.turn_off(clock, settings, now=at(15, 0))
    assert st["dark"] and st["why"] == "off" and st["until"] is None
    assert clock.pushes == [night.APP] and clock.switches == [night.APP]
    st = night.turn_on(clock, settings, now=at(15, 1))
    assert not st["dark"] and night.override() is None
    assert clock.removed == [night.APP]


def test_off_until_morning_ends_on_its_own():
    settings = settings_with(NIGHTLY)
    now = at(21, 30)
    until = night.until_morning(settings, now)
    assert until - now == (9 * 60 + 30) * 60  # 21:30 -> 07:00
    night.turn_off(FakeClock(), settings, until, now=now)
    assert night.dark_now(settings, until - 60) == (True, "off")
    assert night.dark_now(settings, until + 60) == (False, None)  # 07:01, past the schedule


def test_schedule_and_keeping_it_on_for_tonight():
    clock = FakeClock()
    settings = settings_with(NIGHTLY)
    assert night.dark_now(settings, at(23, 30)) == (True, "schedule")
    assert night.dark_now(settings, at(12, 0)) == (False, None)
    st = night.turn_on(clock, settings, now=at(23, 30))  # inside the hours: stay lit tonight
    assert not st["dark"] and st["why"] == "on"
    assert night.dark_now(settings, at(23, 30) + 3600) == (False, "on")
    assert night.dark_now(settings, at(23, 30) + 8 * 3600) == (False, None)  # after 07:00


def test_status_says_when_the_next_change_is():
    settings = settings_with(NIGHTLY)
    st = night.status(settings, at(12, 0))
    assert not st["dark"] and st["until"] == at(23, 0)
    assert night.status(settings_with(), at(12, 0))["until"] is None


def test_watch_puts_the_black_screen_up_once_and_resumes():
    clock = FakeClock()
    settings = settings_with(NIGHTLY)
    t = [at(22, 59)]
    logs = []
    watch = night.Watch(clock, settings, log=logs.append, clock=lambda: t[0])
    assert watch.dark() is False and clock.switches == []
    assert clock.removed == [night.APP]  # a black screen left from a previous run goes
    t[0] = at(23, 0)
    assert watch.dark() is True
    t[0] += 30
    assert watch.dark() is True
    assert clock.switches == [night.APP]  # not again within REASSERT
    t[0] += night.REASSERT
    watch.dark()
    assert clock.switches == [night.APP, night.APP]  # a rebooted clock gets it back
    t[0] = at(23, 0) + 8 * 3600  # 07:00
    assert watch.dark() is False
    assert clock.removed == [night.APP, night.APP]
    assert any("pausing" in line for line in logs) and any("resuming" in line for line in logs)


def test_watch_retries_when_the_clock_is_away():
    clock = FakeClock()
    clock.down = True
    t = [at(23, 30)]
    watch = night.Watch(clock, settings_with(NIGHTLY), log=lambda _: None, clock=lambda: t[0])
    assert watch.dark() is True and clock.switches == []
    clock.down = False
    t[0] += 2
    watch.dark()
    assert clock.switches == [night.APP]


def test_rotation_and_output_do_nothing_while_dark():
    clock = FakeClock()
    slot = config.Slot(seconds=10, screen="sys")
    dark = [True]
    rot = Rotation(clock, [slot], Attention(), held=lambda: 0, dark=lambda: dark[0])
    assert rot.step((0, None)) == (0, None)
    assert clock.switches == []
    out = Output(clock, paused=lambda: dark[0])
    out.show("sys", object())
    assert clock.pushes == []
    dark[0] = False
    rot.step((0, None))
    assert clock.switches == ["sys"]
