"""Live preview: the hold that pauses the rotation, and city search merging."""

import json

from tc002.config import Slot
from tc002.runtime import hold
from tc002.runtime.rotation import Attention, Rotation
from tc002.web import cities


class Clock:
    def __init__(self):
        self.switches = []

    def switch_custom(self, app):
        self.switches.append(app)

    def switch_builtin(self, category, index):
        self.switches.append((category, index))


def test_hold_expires_and_releases(tmp_path):
    path = tmp_path / "hold.json"
    hold.hold(60, path, now=1000)
    assert hold.active(path, now=1030) == 30
    assert hold.active(path, now=1061) == 0
    hold.hold(9999, path, now=0)
    assert hold.active(path, now=0) == hold.MAX_SECONDS  # capped
    hold.release(path)
    assert hold.active(path) == 0


def test_rotation_switches_nothing_while_held_then_reshows():
    clock, held = Clock(), [True]
    pl = Rotation(clock, [Slot(10, screen="claude")], Attention(), held=lambda: held[0])
    state = pl.step((0, None))
    assert clock.switches == []
    held[0] = False
    pl.step(state)
    assert clock.switches == ["claude"]


def test_alerts_also_wait_for_the_hold():
    clock, attention = Clock(), Attention()
    attention.set("claude")
    pl = Rotation(clock, [], attention, held=lambda: True)
    pl.step((0, None))
    assert clock.switches == []


def test_city_search_puts_prefix_matches_first_and_dedupes():
    body = json.dumps(
        {
            "results": [
                {
                    "name": "Melbourne",
                    "latitude": -37.814,
                    "longitude": 144.9633,
                    "admin1": "Victoria",
                    "country": "Australia",
                    "feature_code": "PPLA",
                    "population": 5435590,
                },
                {
                    "name": "Melbourne",
                    "latitude": 28.08,
                    "longitude": -80.6,
                    "admin1": "Florida",
                    "country": "United States",
                    "feature_code": "PPL",
                    "population": 84678,
                },
            ]
        }
    ).encode()
    result = cities.search("Melb", "en", fetch=lambda url: body)
    names = [(r["name"], r["region"]) for r in result["results"]]
    assert result["source"] == "open-meteo"
    assert names == [("Melbourne", "Australia"), ("Melbourne", "Florida, United States")]


def _place(name, code, population, admin1, country="中国", lat=31.0, lon=121.0):
    return {
        "name": name,
        "feature_code": code,
        "population": population,
        "admin1": admin1,
        "country": country,
        "latitude": lat,
        "longitude": lon,
    }


def test_city_search_lists_only_places_someone_would_mean():
    # what the geocoder answers for "上海": the city, five villages and an island
    raw = [
        _place("上海", "PPLA", 24874500, "上海市"),
        _place("上海", "PPL", None, "浙江", lat=29.9),
        _place("上海", "PPL", None, "云南", lat=26.8, lon=100.2),
        _place("上海", "PPL", None, "四川", lat=27.9, lon=102.3),
        _place("上海", "ISL", None, "浙江", lat=30.1, lon=122.1),
    ]
    body = json.dumps({"results": raw}).encode()
    result = cities.search("上海市区", "zh", fetch=lambda url: body)  # no built-in prefix hit
    assert [(r["name"], r["region"]) for r in result["results"]] == [("上海", "中国")]


def test_city_search_falls_back_to_the_largest_small_towns():
    raw = [
        _place("Tiny", "PPL", 120, "A", "X"),
        _place("Tiny", "PPLX", 9000, "B", "X", lat=10),  # a neighbourhood: never listed
        _place("Tiny", "PPL", 800, "C", "X", lat=20),
    ]
    body = json.dumps({"results": raw}).encode()
    result = cities.search("Tiny", "en", fetch=lambda url: body)
    assert [r["region"] for r in result["results"]] == ["C, X", "A, X"]


def test_city_search_offline_and_empty_query():
    def broken(url):
        raise OSError("no network")

    assert cities.search("悉", "zh", fetch=broken)["results"][0]["name"] == "悉尼"
    assert cities.search("", "en")["source"] == "offline"
    assert cities.search("x" * 500, "en", fetch=lambda url: b"{}")["results"] == []
