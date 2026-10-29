"""Built-in app layout and the rotation driver, against an in-memory clock."""

import copy

import pytest

from tc002 import builtins
from tc002.config import Slot
from tc002.device import DeviceError
from tc002.runtime.rotation import Attention, Rotation

SECRET = "oauth-token-must-not-leak"


class FakeClock:
    """Holds the three category configs the way the firmware returns them."""

    def __init__(self):
        self.cfg = {
            "tools": {
                "toolsInfos": {
                    "clock": {"timeFormat": "HH:MM", "enable": True},
                    "weather": {"city": "Sydney", "token": SECRET, "enable": True},
                    "busy": {"enable": False},
                },
                "toolsOrder": list(range(1, 10)),
            },
            "social": {
                "socialInfos": {"xhs": {"uid": "1", "token": SECRET, "enable": True}},
                "socialOrder": list(range(1, 10)),
            },
            "calendar": {
                "calendarInfos": {"google": {"url": "https://x", "enable": True}},
                "calendarOrder": list(range(1, 7)),
            },
        }
        self.switches, self.up = [], True

    def category_config(self, category):
        return copy.deepcopy(self.cfg[category])

    def set_category_config(self, category, body):
        assert set(body) == set(self.cfg[category])  # infos + full order, always
        self.cfg[category] = copy.deepcopy(body)

    def switch_custom(self, app):
        self._switch(("custom", app))

    def switch_builtin(self, category, index):
        self._switch((category, index))

    def _switch(self, what):
        if not self.up:
            raise DeviceError("timed out")
        self.switches.append(what)


def enabled(clock):
    return {
        k
        for cat in clock.cfg.values()
        for infos in [next(v for key, v in cat.items() if key.endswith("Infos"))]
        for k, v in infos.items()
        if v["enable"]
    }


def test_apply_keeps_only_named_builtins_and_preserves_settings():
    clock = FakeClock()
    changed = builtins.apply_enabled(clock, {"clock"})
    assert enabled(clock) == {"clock"}
    assert sorted(changed) == ["google=off", "weather=off", "xhs=off"]
    assert clock.cfg["tools"]["toolsInfos"]["weather"]["city"] == "Sydney"


def test_snapshot_has_no_credentials_and_restores(tmp_path):
    clock = FakeClock()
    snap = builtins.snapshot(clock)
    assert SECRET not in repr(snap)
    path, saved = builtins.save_original(snap, tmp_path)
    builtins.apply_enabled(clock, set())
    assert enabled(clock) == set()
    _, loaded = builtins.load_original(tmp_path)
    builtins.restore(clock, loaded)
    assert enabled(clock) == {"clock", "weather", "xhs", "google"}
    assert saved and SECRET not in path.read_text()


def test_second_apply_never_overwrites_the_original(tmp_path):
    first = {"tools": {"enable": {"clock": True}, "order": []}}
    builtins.save_original(first, tmp_path)
    _, saved = builtins.save_original({"tools": {"enable": {}, "order": []}}, tmp_path)
    assert not saved
    assert builtins.load_original(tmp_path)[1] == first


def test_unknown_builtin_fails_before_touching_the_clock():
    clock = FakeClock()
    before = copy.deepcopy(clock.cfg)
    with pytest.raises(ValueError, match="unknown built-in"):
        builtins.apply_enabled(clock, {"fax"})
    assert clock.cfg == before


def run(rotation, ticks, clock_values):
    state = (0, None)
    for _ in range(ticks):
        state = rotation.step(state)
        clock_values[0] += 1


SLOTS = [Slot(3, screen="claude"), Slot(2, builtin="clock")]


def test_rotation_rotates_custom_and_builtin_slots():
    clock, now = FakeClock(), [0.0]
    pl = Rotation(clock, SLOTS, Attention(), clock=lambda: now[0])
    run(pl, 7, now)
    assert clock.switches == [("custom", "claude"), ("tools", 1), ("custom", "claude")]


def test_alert_takes_over_then_rotation_resumes():
    clock, now, attention = FakeClock(), [0.0], Attention()
    pl = Rotation(clock, SLOTS, attention, clock=lambda: now[0])
    state = pl.step((0, None))  # claude
    state = pl.step((1, None))  # clock
    attention.set("claude")
    for _ in range(3):
        state = pl.step(state)
    attention.set(None)
    pl.step(state)
    assert clock.switches == [
        ("custom", "claude"),
        ("tools", 1),
        ("custom", "claude"),
        ("tools", 1),
    ]


def test_takeover_off_ignores_alerts():
    clock, now, attention = FakeClock(), [0.0], Attention()
    pl = Rotation(
        clock, [Slot(10, builtin="clock")], attention, takeover=False, clock=lambda: now[0]
    )
    attention.set("claude")
    pl.step((0, None))
    assert clock.switches == [("tools", 1)]


def test_offline_clock_is_retried_without_advancing():
    clock, now = FakeClock(), [0.0]
    clock.up = False
    pl = Rotation(clock, SLOTS, Attention(), clock=lambda: now[0])
    state = pl.step((0, None))
    assert state == (0, None) and clock.switches == []
    clock.up = True
    pl.step(state)
    assert clock.switches == [("custom", "claude")]
