"""Settings: the versioned `tc002.toml` plus machine-local state.

The repository's `tc002.toml` is the single source of every setting tc002 manages:
screens, rotation, which built-in apps stay on, display settings and built-in app
settings. `tc002 layout apply` and the web UI push it to the clock.

Machine-local facts — the clock's IP, which config file to use, the clock's original
layout — live under ~/.config/tc002 and are never committed.
"""

import json
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import builtins, device_settings

STATE_DIR = Path(os.environ.get("TC002_STATE_DIR", "~/.config/tc002")).expanduser()
LOCAL_FILE = STATE_DIR / "local.json"


# Allowed keys per section; None = validated in depth elsewhere (device_settings).
SECTION_KEYS = {
    "screens": {"enabled"},
    "device": {"keep_builtins"},
    "display": None,
    "apps": None,
    "rotation": {"slots"},
    "alerts": {"takeover"},
}


class ConfigError(ValueError):
    """tc002.toml is missing a field or holds an invalid value."""


@dataclass(frozen=True)
class Slot:
    """One rotation entry: a custom screen (`screen`) or a built-in app (`builtin`)."""

    seconds: float
    screen: str | None = None
    builtin: str | None = None

    @property
    def label(self):
        return self.screen or f"builtin:{self.builtin}"


@dataclass(frozen=True)
class Settings:
    screens: tuple[str, ...] = ("claude", "sys")
    rotation: tuple[Slot, ...] = ()
    keep_builtins: tuple[str, ...] = ("clock",)
    alert_takeover: bool = True
    display: dict = field(default_factory=dict)  # global settings, keys as in /setConfig
    apps: dict = field(default_factory=dict)  # built-in app settings, see device_settings
    source: str = "<built-in defaults>"


def _parse(data, source):
    from .screens import SCREENS  # deferred: screens import runtime modules

    known_screens = set(SCREENS)
    if "playlist" in data:  # the section's name before 0.2; read it, write [rotation]
        if "rotation" in data:
            raise ConfigError(f"{source}: use [rotation] only; [playlist] is its old name")
        data = {("rotation" if k == "playlist" else k): v for k, v in data.items()}
    for section, keys in SECTION_KEYS.items():
        if section not in data:
            continue
        if keys is not None and (extra := set(data[section]) - keys):
            raise ConfigError(f"{source}: unknown key(s) in [{section}]: {sorted(extra)}")
    if extra := set(data) - set(SECTION_KEYS):
        raise ConfigError(f"{source}: unknown section(s) {sorted(extra)}")
    screens = tuple(data.get("screens", {}).get("enabled", ["claude", "sys"]))
    if bad := set(screens) - known_screens:
        raise ConfigError(f"{source}: unknown screens {sorted(bad)}; known {sorted(known_screens)}")

    slots = []
    for i, raw in enumerate(data.get("rotation", {}).get("slots", [])):
        where = f"{source}: rotation.slots[{i}]"
        if ("screen" in raw) == ("builtin" in raw):
            raise ConfigError(f"{where}: set exactly one of `screen` or `builtin`")
        if "screen" in raw and raw["screen"] not in screens:
            raise ConfigError(f"{where}: screen {raw['screen']!r} is not in screens.enabled")
        if "builtin" in raw:
            try:
                builtins.lookup(raw["builtin"])
            except ValueError as exc:
                raise ConfigError(f"{where}: {exc}") from None
        seconds = raw.get("seconds", 15)
        if not isinstance(seconds, int | float) or seconds < 3:
            raise ConfigError(f"{where}: seconds must be a number >= 3")
        slots.append(Slot(float(seconds), raw.get("screen"), raw.get("builtin")))

    device = data.get("device", {})
    keep = tuple(device.get("keep_builtins", ["clock"]))
    for name in keep:
        try:
            builtins.lookup(name)
        except ValueError as exc:
            raise ConfigError(f"{source}: device.keep_builtins: {exc}") from None
    for slot in slots:
        if slot.builtin and slot.builtin not in keep:
            raise ConfigError(
                f"{source}: rotation uses built-in {slot.builtin!r}, "
                "which must also be listed in device.keep_builtins"
            )
    display, apps = data.get("display", {}), data.get("apps", {})
    if problems := device_settings.validate_display(display) + device_settings.validate_apps(apps):
        raise ConfigError(f"{source}: " + "; ".join(problems))

    return Settings(
        screens=screens,
        rotation=tuple(slots),
        keep_builtins=keep,
        alert_takeover=bool(data.get("alerts", {}).get("takeover", True)),
        display=display,
        apps=apps,
        source=source,
    )


def parse(data, source="<input>"):
    """Validate a tc002.toml-shaped dict (e.g. from the web UI) into Settings."""
    return _parse(data, source)


def to_data(settings):
    """Settings back to the tc002.toml dict shape (inverse of `parse`)."""
    return {
        "screens": {"enabled": list(settings.screens)},
        "device": {"keep_builtins": list(settings.keep_builtins)},
        "display": settings.display,
        "apps": settings.apps,
        "rotation": {
            "slots": [
                {"screen": s.screen, "seconds": s.seconds}
                if s.screen
                else {"builtin": s.builtin, "seconds": s.seconds}
                for s in settings.rotation
            ]
        },
        "alerts": {"takeover": settings.alert_takeover},
    }


def path():
    """The tc002.toml in use, or None when running on built-in defaults."""
    chosen = os.environ.get("TC002_CONFIG") or local().get("config")
    return Path(chosen).expanduser() if chosen else None


def load(path=None):
    """Read settings from `path`, else the file saved by `tc002 setup`, else defaults."""
    path = path or os.environ.get("TC002_CONFIG") or local().get("config")
    if path is None:
        return Settings()
    path = Path(path).expanduser()
    try:
        return _parse(tomllib.loads(path.read_text()), str(path))
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from None


def local():
    """Machine-local state: {"host": ..., "config": ...}."""
    try:
        return json.loads(LOCAL_FILE.read_text())
    except OSError, json.JSONDecodeError:
        return {}


def save_local(**updates):
    data = local() | {k: v for k, v in updates.items() if v is not None}
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_FILE.write_text(json.dumps(data, indent=2))
    return data


def host(cli_host=None):
    return cli_host or os.environ.get("TC002_HOST") or local().get("host")
