"""The clock following this Mac's time zone: reading the zone, sync, and the service."""

import copy

import pytest

from tc002 import config, sync, tz
from tc002.device import DeviceError

SYDNEY = ("Australia/Sydney", "AEST-10AEDT,M10.1.0,M4.1.0/3")
TOKYO = ("Asia/Tokyo", "JST-9")


def test_mac_zone_reads_the_posix_footer(tmp_path):
    zone = tmp_path / "zoneinfo" / "Australia" / "Sydney"
    zone.parent.mkdir(parents=True)
    zone.write_bytes(b"TZif2" + b"\x00" * 40 + b"\nAEST-10AEDT,M10.1.0,M4.1.0/3\n")
    link = tmp_path / "localtime"
    link.symlink_to(zone)
    assert tz.mac_zone(link) == SYDNEY


@pytest.mark.parametrize("data", [b"not a zone file", b"TZif1\x00\x00", b"TZif2\x00\n\n"])
def test_mac_zone_refuses_files_without_a_rule(tmp_path, data):
    path = tmp_path / "zone"
    path.write_bytes(data)
    with pytest.raises(ValueError):
        tz.mac_zone(path)


def test_this_mac_has_a_zone():
    name, rule = tz.mac_zone()
    assert name and rule


class Clock:
    def __init__(self, ex=None):
        self.cfg = {
            "timezone": "UTC+8",
            "carouselSpeed": 0,
            "timezoneEx": ex or {"location": "", "customPosixEnabled": False, "customPosix": ""},
        }
        self.sets = []
        self.down = False

    def config(self):
        if self.down:
            raise DeviceError("offline")
        return copy.deepcopy(self.cfg)

    def set_config(self, **fields):
        self.sets.append(fields)
        self.cfg |= copy.deepcopy(fields)

    def category_config(self, category):
        from tc002.device import CATEGORY_ENDPOINTS

        _, _, infos_key, order_key = CATEGORY_ENDPOINTS[category]
        return {infos_key: {}, order_key: []}

    def set_category_config(self, category, body):
        pass


def test_sync_auto_sends_the_rule_and_a_fixed_zone_turns_it_off(tmp_path, monkeypatch):
    monkeypatch.setattr(tz, "mac_zone", lambda: SYDNEY)
    clock = Clock()
    sync.apply(clock, config.parse({"display": {"timezone": "auto"}}), tmp_path)
    assert clock.cfg["timezoneEx"] == {
        "location": SYDNEY[0],
        "customPosixEnabled": True,
        "customPosix": SYDNEY[1],
    }
    assert clock.cfg["timezone"] == "UTC+8"  # untouched: the rule wins on the clock
    assert sync.apply(clock, config.parse({"display": {"timezone": "auto"}}), tmp_path) == []

    sync.apply(clock, config.parse({"display": {"timezone": "UTC+9"}}), tmp_path)
    assert clock.cfg["timezone"] == "UTC+9"
    assert clock.cfg["timezoneEx"] == {"location": "", "customPosixEnabled": False, "customPosix": ""}


def test_restore_puts_the_old_zone_back(tmp_path, monkeypatch):
    monkeypatch.setattr(tz, "mac_zone", lambda: SYDNEY)
    clock = Clock()
    sync.apply(clock, config.parse({"display": {"timezone": "auto"}}), tmp_path)
    sync.restore(clock, tmp_path)
    assert clock.cfg["timezoneEx"]["customPosixEnabled"] is False


def test_auto_is_a_valid_choice():
    assert config.parse({"display": {"timezone": "auto"}}).display["timezone"] == "auto"
    with pytest.raises(config.ConfigError):
        config.parse({"display": {"timezone": "Sydney"}})


def test_follow_sends_once_then_again_when_the_mac_moves():
    clock = Clock()
    now, zone, logs = [0.0], [SYDNEY], []
    follow = tz.Follow(clock, log=logs.append, clock=lambda: now[0], zone=lambda: zone[0])
    follow.tick()
    assert clock.cfg["timezoneEx"]["customPosix"] == SYDNEY[1] and len(clock.sets) == 1
    now[0] += 30
    follow.tick()  # not time to look again yet
    now[0] += tz.CHECK_EVERY
    follow.tick()  # same zone: nothing sent
    assert len(clock.sets) == 1
    zone[0] = TOKYO
    now[0] += tz.CHECK_EVERY
    follow.tick()
    assert clock.cfg["timezoneEx"]["location"] == "Asia/Tokyo" and len(clock.sets) == 2
    assert any("Asia/Tokyo" in line for line in logs)


def test_follow_leaves_a_clock_that_already_matches_and_retries_when_away():
    clock = Clock({"location": SYDNEY[0], "customPosixEnabled": True, "customPosix": SYDNEY[1]})
    now = [0.0]
    follow = tz.Follow(clock, log=lambda _: None, clock=lambda: now[0], zone=lambda: SYDNEY)
    follow.tick()
    assert clock.sets == []

    away = Clock()
    away.down = True
    follow = tz.Follow(away, log=lambda _: None, clock=lambda: now[0], zone=lambda: SYDNEY)
    follow.tick()
    away.down = False
    now[0] += tz.CHECK_EVERY
    follow.tick()
    assert away.cfg["timezoneEx"]["customPosix"] == SYDNEY[1]
