"""Settings: the versioned `tc002.toml` plus machine-local state.

The repository's `tc002.toml` holds what to show (screens, playlist, which built-in
apps stay on). Machine-local facts — the clock's IP, which config file to use, snapshots
of the device's own settings — live under ~/.config/tc002 and are never committed.
"""

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import builtins

STATE_DIR = Path(os.environ.get("TC002_STATE_DIR", "~/.config/tc002")).expanduser()
LOCAL_FILE = STATE_DIR / "local.json"


class ConfigError(ValueError):
    """tc002.toml is missing a field or holds an invalid value."""


@dataclass(frozen=True)
class Slot:
    """One playlist entry: a custom screen (`screen`) or a built-in app (`builtin`)."""

    seconds: float
    screen: str | None = None
    builtin: str | None = None

    @property
    def label(self):
        return self.screen or f"builtin:{self.builtin}"


@dataclass(frozen=True)
class Settings:
    screens: tuple[str, ...] = ("claude", "sys")
    playlist: tuple[Slot, ...] = ()
    keep_builtins: tuple[str, ...] = ("clock",)
    alert_takeover: bool = True
    brightness: str | None = None
    source: str = "<built-in defaults>"


def _parse(data, source):
    from .screens import SCREENS  # deferred: screens import runtime modules

    known_screens = set(SCREENS)
    screens = tuple(data.get("screens", {}).get("enabled", ["claude", "sys"]))
    if bad := set(screens) - known_screens:
        raise ConfigError(f"{source}: unknown screens {sorted(bad)}; known {sorted(known_screens)}")

    slots = []
    for i, raw in enumerate(data.get("playlist", {}).get("slots", [])):
        where = f"{source}: playlist.slots[{i}]"
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
                f"{source}: playlist uses built-in {slot.builtin!r}, "
                "which must also be listed in device.keep_builtins"
            )
    brightness = device.get("brightness")
    if brightness not in (None, "low", "mid", "high"):
        raise ConfigError(f"{source}: device.brightness must be low, mid or high")

    return Settings(
        screens=screens,
        playlist=tuple(slots),
        keep_builtins=keep,
        alert_takeover=bool(data.get("alerts", {}).get("takeover", True)),
        brightness=brightness,
        source=source,
    )


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
