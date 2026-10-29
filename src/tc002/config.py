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

from . import builtins, device_settings, paths

MIN_SLOT_SECONDS, MAX_SLOT_SECONDS = 3, 600  # how long one rotation slot may show
CYCLE, SINGLE = "cycle", "single"  # [rotation] mode: step through the slots, or hold one
UI_PORT = 8742  # `tc002 ui` default
STATE_DIR = paths.STATE_DIR
LOCAL_FILE = STATE_DIR / "local.json"


# Allowed keys per section; None = validated in depth elsewhere (device_settings).
SECTION_KEYS = {
    "screens": {"enabled"},
    "device": {"keep_builtins"},
    "display": None,
    "apps": None,
    "rotation": {"slots", "mode", "show"},
    "alerts": {"takeover"},
    "appearance": {"led_theme", "ui_palette"},
    "screen": None,  # [screen.<name>] options, validated by screens/options.py
    "connections": None,  # [connections.<name>] plain settings, validated by connections.py
}
DEFAULT_APPEARANCE = {"led_theme": "match", "ui_palette": "paper"}


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
    rotation_mode: str = CYCLE
    pinned: Slot | None = None  # what SINGLE mode holds on screen
    keep_builtins: tuple[str, ...] = ("clock",)
    alert_takeover: bool = True
    display: dict = field(default_factory=dict)  # global settings, keys as in /setConfig
    apps: dict = field(default_factory=dict)  # built-in app settings, see device_settings
    appearance: dict = field(default_factory=lambda: dict(DEFAULT_APPEARANCE))
    screen_options: dict = field(default_factory=dict)  # [screen.<name>] tables
    connections: dict = field(default_factory=dict)  # [connections.<name>] (never secrets)
    source: str = "<built-in defaults>"

    @property
    def led_theme(self):
        """The LED theme in effect, with "match" resolved to the UI's palette."""
        from .render import themes

        return themes.resolve(self.appearance["led_theme"], self.appearance["ui_palette"])

    @property
    def schedule(self):
        """The slots the clock steps through: the rotation, or just the pinned one."""
        if self.rotation_mode == SINGLE:
            return (self.pinned,)
        return self.rotation


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

    rotation = data.get("rotation", {})
    slots = [
        _slot(raw, f"{source}: rotation.slots[{i}]", screens)
        for i, raw in enumerate(rotation.get("slots", []))
    ]
    mode = rotation.get("mode", CYCLE)
    if mode not in (CYCLE, SINGLE):
        raise ConfigError(f"{source}: rotation.mode must be {CYCLE!r} or {SINGLE!r}")
    pinned = None
    if "show" in rotation:
        pinned = _slot(
            {**rotation["show"], "seconds": MAX_SLOT_SECONDS}, f"{source}: rotation.show", screens
        )
    if mode == SINGLE and pinned is None:
        raise ConfigError(f"{source}: rotation.mode = {SINGLE!r} needs rotation.show")

    device = data.get("device", {})
    keep = tuple(device.get("keep_builtins", ["clock"]))
    for name in keep:
        try:
            builtins.lookup(name)
        except ValueError as exc:
            raise ConfigError(f"{source}: device.keep_builtins: {exc}") from None
    for slot in [*slots, pinned]:
        if slot and slot.builtin and slot.builtin not in keep:
            raise ConfigError(
                f"{source}: rotation uses built-in {slot.builtin!r}, "
                "which must also be listed in device.keep_builtins"
            )
    display, apps = data.get("display", {}), data.get("apps", {})
    if problems := device_settings.validate_display(display) + device_settings.validate_apps(apps):
        raise ConfigError(f"{source}: " + "; ".join(problems))

    screen_options = data.get("screen", {})
    from .screens import options as screen_options_rules

    if problems := screen_options_rules.validate(SCREENS, screen_options):
        raise ConfigError(f"{source}: " + "; ".join(problems))
    from . import connections as connection_rules

    connections = data.get("connections", {})
    if problems := connection_rules.validate(connections):
        raise ConfigError(f"{source}: " + "; ".join(problems))
    appearance = {**DEFAULT_APPEARANCE, **data.get("appearance", {})}
    if problems := _appearance_problems(appearance):
        raise ConfigError(f"{source}: " + "; ".join(problems))

    return Settings(
        screen_options=screen_options,
        connections=connections,
        appearance=appearance,
        screens=screens,
        rotation=tuple(slots),
        rotation_mode=mode,
        pinned=pinned,
        keep_builtins=keep,
        alert_takeover=bool(data.get("alerts", {}).get("takeover", True)),
        display=display,
        apps=apps,
        source=source,
    )


def _slot(raw, where, screens):
    if not isinstance(raw, dict) or ("screen" in raw) == ("builtin" in raw):
        raise ConfigError(f"{where}: set exactly one of `screen` or `builtin`")
    if "screen" in raw and raw["screen"] not in screens:
        raise ConfigError(f"{where}: screen {raw['screen']!r} is not in screens.enabled")
    if "builtin" in raw:
        try:
            builtins.lookup(raw["builtin"])
        except ValueError as exc:
            raise ConfigError(f"{where}: {exc}") from None
    seconds = raw.get("seconds", 15)
    if not isinstance(seconds, int | float) or not MIN_SLOT_SECONDS <= seconds <= MAX_SLOT_SECONDS:
        raise ConfigError(
            f"{where}: seconds must be a number from {MIN_SLOT_SECONDS} to {MAX_SLOT_SECONDS}"
        )
    return Slot(float(seconds), raw.get("screen"), raw.get("builtin"))


def _slot_data(slot, seconds=True):
    data = {"screen": slot.screen} if slot.screen else {"builtin": slot.builtin}
    return {**data, "seconds": slot.seconds} if seconds else data


def _appearance_problems(appearance):
    from .render import themes

    problems = []
    if appearance["led_theme"] not in themes.names():
        problems.append(f"appearance.led_theme must be one of {themes.names()}")
    if appearance["ui_palette"] not in themes.UI_PALETTES:
        problems.append(f"appearance.ui_palette must be one of {list(themes.UI_PALETTES)}")
    return problems


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
            "slots": [_slot_data(s) for s in settings.rotation],
            **({"mode": settings.rotation_mode} if settings.rotation_mode != CYCLE else {}),
            **({"show": _slot_data(settings.pinned, False)} if settings.pinned else {}),
        },
        "alerts": {"takeover": settings.alert_takeover},
        "appearance": dict(settings.appearance),
        "screen": {k: dict(v) for k, v in settings.screen_options.items()},
        "connections": {k: dict(v) for k, v in settings.connections.items()},
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
