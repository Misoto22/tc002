"""What front ends show and validate against: names, allowed values and limits. Plain
data only, taken from the units that define them, so a front end never imports those
units to build a menu, a JSON Schema or argparse choices."""

from .. import config
from ..clock import builtins, device_settings
from ..clock.device import MIN_FIRMWARE
from ..config import presets
from ..games import GAMES
from ..render import font, themes
from ..render.canvas import HEIGHT, WIDTH
from ..render.palette import hex_palette
from ..screens import NETWORKED, SCREENS, message, stale
from ..screens import options as screen_options
from ..screens import usage as usage_screen
from ..state import sessions

UI_PORT = config.UI_PORT
SCREEN_NAMES = list(SCREENS)
BUILTIN_NAMES = list(builtins.CATALOGUE)
COLORS = dict(message.COLORS)  # name -> "#RRGGBB"
ALERT_KINDS = list(message.ICONS)
MESSAGE_MAX_CHARS, ALERT_MAX_CHARS = message.MAX_CHARS, message.ALERT_MAX_CHARS
MANUAL_EVENTS = list(sessions.MANUAL)  # `tc002 event <kind>`
DISPLAY = dict(device_settings.DISPLAY)  # key -> (kind, label, options or (min, max))
BRIGHTNESS_LEVELS = list(device_settings.BRIGHTNESS_LEVELS)
BRIGHTNESS_RANGE = device_settings.BRIGHTNESS_RANGE
TIMEZONES = list(device_settings.TIMEZONES)  # "auto" follows this Mac
TOKEN_APPS = device_settings.TOKEN_APPS
CONFIG_SECTIONS = sorted(config.SECTION_KEYS)
GAME_KEYS = {name: list(g.KEYS) for name, g in GAMES.items()}
# cheap, local and quiet to sample, so the UI previews them with real data
LIVE_SCREENS = set(SCREENS) - {"sys"} - NETWORKED


def ui():
    """The fixed part of what the settings UI needs on load."""
    return {
        "staleAfter": {"age": stale.STALE_AFTER, "noData": stale.NO_DATA_AFTER},
        "catalogue": [
            {"key": k, "category": b.category, "index": b.index}
            for k, b in builtins.CATALOGUE.items()
        ],
        "screens": SCREEN_NAMES,
        "screenOptions": screen_options.describe(SCREENS),
        "liveScreens": sorted(LIVE_SCREENS),
        "networked": sorted(NETWORKED),
        "games": GAME_KEYS,
        "schema": device_settings.schema(),
        "colors": COLORS,
        "alertKinds": ALERT_KINDS,
        "messageMaxChars": MESSAGE_MAX_CHARS,
        "limits": {"warn": usage_screen.WARN, "critical": usage_screen.CRITICAL},
        "slotSeconds": {"min": config.MIN_SLOT_SECONDS, "max": config.MAX_SLOT_SECONDS},
        "presets": presets.describe(),
        "ledThemes": themes.names(),
        "minFirmware": ".".join(map(str, MIN_FIRMWARE)),
        "timezones": TIMEZONES,
    }


def led():
    """Pixel fonts and LED palette, so browser previews draw exactly what the clock would."""
    return {
        "font": {"big": font.BIG, "small": font.SMALL},
        "palette": hex_palette(),
        "size": {"width": WIDTH, "height": HEIGHT},
    }
