"""tc002.toml parsing and validation, including the repository's own file."""

from pathlib import Path

import pytest

from tc002 import config

REPO_CONFIG = Path(__file__).resolve().parent.parent / "tc002.toml"


def write(tmp_path, body):
    path = tmp_path / "tc002.toml"
    path.write_text(body)
    return path


def test_repository_config_is_valid():
    settings = config.load(REPO_CONFIG)
    assert settings.screens == ("claude", "sys")
    assert [s.label for s in settings.rotation] == ["claude", "sys", "builtin:clock"]


def test_no_config_means_builtin_defaults(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOCAL_FILE", tmp_path / "missing.json")
    monkeypatch.delenv("TC002_CONFIG", raising=False)
    assert config.load() == config.Settings()


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ('[screens]\nenabled = ["nope"]', "unknown screens"),
        ('[rotation]\nslots = [{ screen = "claude", builtin = "clock" }]', "exactly one"),
        ('[rotation]\nslots = [{ builtin = "weather" }]', "keep_builtins"),
        ('[rotation]\nslots = [{ screen = "claude", seconds = 1 }]', "seconds"),
        ('[device]\nkeep_builtins = ["fax"]', "unknown built-in"),
        ('[device]\nbrightness = "max"', "unknown key"),
        ('[display]\nbrightness = { level = "max" }', "brightness.level"),
        ("[display]\nbrightness = { low = 90, mid = 50, high = 100 }", "must rise"),
        ("[display]\nvolume = 9", "0-6"),
        ('[display]\ncolour = "red"', "not a known setting"),
        ('[apps.clock]\ntimeFormat = "24h"', "timeFormat"),
        ('[apps.weather]\ntoken = "secret"', "not a known setting"),
        ("[apps.weather.displayInfo]\ndisplayAqi = false", "at least one"),
        ('[apps.xhs]\nuid = "1"', "settings exist only"),
        ("[surprise]\nx = 1", "unknown section"),
        ("[screens\n", "Expected"),
    ],
)
def test_invalid_configs_are_rejected_with_a_pointer(tmp_path, body, message):
    with pytest.raises(config.ConfigError, match=message):
        config.load(write(tmp_path, body))


def test_missing_file_is_a_config_error(tmp_path):
    with pytest.raises(config.ConfigError, match="not found"):
        config.load(tmp_path / "nope.toml")


def test_local_state_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "STATE_DIR", tmp_path)
    monkeypatch.setattr(config, "LOCAL_FILE", tmp_path / "local.json")
    monkeypatch.delenv("TC002_HOST", raising=False)
    config.save_local(host="10.0.0.9", config=None)
    config.save_local(config="/x/tc002.toml")
    assert config.local() == {"host": "10.0.0.9", "config": "/x/tc002.toml"}
    assert config.host() == "10.0.0.9"
    assert config.host("1.2.3.4") == "1.2.3.4"


def test_legacy_playlist_section_is_read_as_rotation(tmp_path):
    settings = config.load(
        write(tmp_path, '[playlist]\nslots = [{ screen = "claude", seconds = 9 }]')
    )
    assert [s.label for s in settings.rotation] == ["claude"]
    both = "[playlist]\nslots = []\n[rotation]\nslots = []"
    with pytest.raises(config.ConfigError, match="old name"):
        config.load(write(tmp_path, both))
