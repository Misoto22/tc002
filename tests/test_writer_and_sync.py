"""tc002.toml writing and pushing settings to the clock."""

import copy
import tomllib

from tc002 import config, config_writer, sync

FULL = {
    "screens": {"enabled": ["claude", "sys"]},
    "device": {"keep_builtins": ["clock", "weather"]},
    "display": {
        "volume": 2,
        "timezone": "UTC+10",
        "showWeek": False,
        "brightness": {"level": "mid", "low": 20, "mid": 60, "high": 100},
    },
    "apps": {
        "clock": {"timeFormat": "HH:MM:SS"},
        "weather": {"city": 'Syd "ney"', "displayInfo": {"displayAqi": True}},
    },
    "rotation": {
        "slots": [{"screen": "sys", "seconds": 12.5}, {"builtin": "weather", "seconds": 20}]
    },
    "alerts": {"takeover": False},
    "appearance": {"led_theme": "kohaku", "ui_palette": "ai"},
}


def test_dump_round_trips_every_field(tmp_path):
    settings = config.parse(copy.deepcopy(FULL))
    path = tmp_path / "tc002.toml"
    config_writer.save(settings, path)
    assert tomllib.loads(path.read_text()) == FULL
    assert config.load(path) == config.parse(copy.deepcopy(FULL), str(path))


def test_empty_sections_are_written_as_commented_examples(tmp_path):
    path = tmp_path / "tc002.toml"
    config_writer.save(config.Settings(), path)
    text = path.read_text()
    assert "# [display]" in text and "# [apps.clock]" in text
    assert "display" not in tomllib.loads(text)


class Clock:
    def __init__(self):
        self.global_cfg = {
            "brightness": {"level": "high", "low": 50, "mid": 80, "high": 100},
            "volume": 0,
            "timezone": "UTC+8",
            "carouselSpeed": 30,
        }
        self.cats = {
            "tools": {
                "toolsInfos": {
                    "clock": {"timeFormat": "HH:MM", "enable": True},
                    "weather": {
                        "city": "Beijing",
                        "token": "secret-key",
                        "displayInfo": {"displayTemperature": True, "displayAqi": False},
                        "enable": False,
                    },
                },
                "toolsOrder": list(range(1, 10)),
            },
            "social": {"socialInfos": {"xhs": {"enable": True}}, "socialOrder": list(range(1, 10))},
            "calendar": {"calendarInfos": {}, "calendarOrder": list(range(1, 7))},
        }
        self.set_calls = []

    def config(self):
        return copy.deepcopy(self.global_cfg)

    def set_config(self, **fields):
        self.set_calls.append(fields)
        self.global_cfg |= copy.deepcopy(fields)

    def category_config(self, category):
        return copy.deepcopy(self.cats[category])

    def set_category_config(self, category, body):
        self.cats[category] = copy.deepcopy(body)


def test_apply_pushes_display_apps_and_builtins_then_restore_undoes(tmp_path):
    clock = Clock()
    settings = config.parse(copy.deepcopy(FULL))
    changes = sync.apply(clock, settings, tmp_path)

    assert clock.global_cfg["brightness"] == {"level": "mid", "low": 20, "mid": 60, "high": 100}
    assert clock.global_cfg["volume"] == 2 and clock.global_cfg["carouselSpeed"] == 0
    weather = clock.cats["tools"]["toolsInfos"]["weather"]
    assert weather["enable"] and weather["city"] == 'Syd "ney"'
    assert weather["token"] == "secret-key"  # untouched
    assert weather["displayInfo"] == {"displayTemperature": True, "displayAqi": True}  # merged
    assert not clock.cats["social"]["socialInfos"]["xhs"]["enable"]
    assert any("volume" in c for c in changes)

    assert "secret-key" not in (tmp_path / "original-layout.json").read_text()
    sync.restore(clock, tmp_path)
    assert clock.global_cfg["volume"] == 0 and clock.global_cfg["carouselSpeed"] == 30
    assert clock.cats["tools"]["toolsInfos"]["weather"]["city"] == "Beijing"
    assert clock.cats["social"]["socialInfos"]["xhs"]["enable"]


def test_apply_twice_changes_nothing_the_second_time(tmp_path):
    clock = Clock()
    settings = config.parse(copy.deepcopy(FULL))
    sync.apply(clock, settings, tmp_path)
    calls = len(clock.set_calls)
    assert sync.apply(clock, settings, tmp_path) == []
    assert len(clock.set_calls) == calls


def test_social_account_ids_sync_to_the_social_category():
    from tc002 import sync

    class Clock:
        def __init__(self):
            self.social = {
                "socialInfos": {"youtube": {"enable": True, "token": "kept"}},
                "socialOrder": [],
            }
            self.writes = []

        def category_config(self, category):
            return copy.deepcopy(self.social) if category == "social" else {}

        def set_category_config(self, category, body):
            self.writes.append((category, body))

    clock = Clock()
    changes = sync._apply_apps(clock, {"youtube": {"uid": "UC123"}})
    assert changes == ["youtube.uid -> UC123"]
    ((category, body),) = clock.writes
    assert category == "social" and body["socialInfos"]["youtube"]["token"] == "kept"
    assert body["socialOrder"]  # a complete order, as the clock requires
