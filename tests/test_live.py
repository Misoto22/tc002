"""Live preview: the hold that pauses the playlist, and city search merging."""

import json

from tc002.config import Slot
from tc002.runtime import hold
from tc002.runtime.playlist import Attention, Playlist
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


def test_playlist_switches_nothing_while_held_then_reshows():
    clock, held = Clock(), [True]
    pl = Playlist(clock, [Slot(10, screen="claude")], Attention(), held=lambda: held[0])
    state = pl.step((0, None))
    assert clock.switches == []
    held[0] = False
    pl.step(state)
    assert clock.switches == ["claude"]


def test_alerts_also_wait_for_the_hold():
    clock, attention = Clock(), Attention()
    attention.set("claude")
    pl = Playlist(clock, [], attention, held=lambda: True)
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
                },
                {
                    "name": "Melbourne",
                    "latitude": 28.08,
                    "longitude": -80.6,
                    "admin1": "Florida",
                    "country": "United States",
                },
            ]
        }
    ).encode()
    result = cities.search("Melb", "en", fetch=lambda url: body)
    names = [(r["name"], r["region"]) for r in result["results"]]
    assert result["source"] == "open-meteo"
    assert names == [("Melbourne", "Australia"), ("Melbourne", "Florida, United States")]


def test_city_search_offline_and_empty_query():
    def broken(url):
        raise OSError("no network")

    assert cities.search("悉", "zh", fetch=broken)["results"][0]["name"] == "悉尼"
    assert cities.search("", "en")["source"] == "offline"
    assert cities.search("x" * 500, "en", fetch=lambda url: b"{}")["results"] == []
