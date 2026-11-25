"""JSON API behind `tc002 ui`: read everything, change tc002.toml, act on the clock.

A thin front end over the application layer (`tc002.app.App`): each action checks the
shape of the request, calls one App method and returns its result. Saving goes through
`App.save_config` (validate, write tc002.toml, `sync.apply`, restart the service), the
same path the CLI and the MCP server use.
"""

from pathlib import Path

from .. import builtins, config, device_settings, presets
from ..app import App
from ..device import MIN_FIRMWARE
from ..games import GAMES
from ..render import font, themes
from ..render.canvas import HEIGHT, WIDTH
from ..render.palette import hex_palette
from ..runtime import freshness
from ..screens import NETWORKED, SCREENS, message, stale
from ..screens import options as screen_options
from ..screens import usage as usage_screen
from . import cities
from .agents import Agents
from .errors import ApiError
from .host_actions_api import HostActions
from .play_actions import PlayActions
from .previews import LIVE_SCREENS, Previews
from .screen_actions import ScreenActions
from .setup_actions import SetupActions


class Api(SetupActions, PlayActions, HostActions, Previews, ScreenActions):
    """Every API action; groups of them live in the *_actions modules."""

    def __init__(self, host, config_path, state_dir=None):
        # the clock is asked through self._device, so a test can stand in for it
        self.app = App(host, config_path, state_dir, timeout=4, device=lambda: self._device())
        self.agents = Agents()
        self.game = None  # the one game being played, if any (games/session.py)

    host = property(lambda self: self.app.host, lambda self, v: setattr(self.app, "host", v))
    config_path = property(
        lambda self: self.app.config_path, lambda self, v: setattr(self.app, "config_path", v)
    )
    state_dir = property(lambda self: self.app.state_dir)

    # -- helpers ------------------------------------------------------------------

    def _device(self):
        return self.app.new_device()

    def _settings(self):
        return self.app.settings()

    def _settings_or_none(self):
        return self.app.settings_or_none()

    def _led_theme(self):
        return self.app.led_theme()

    # -- reads --------------------------------------------------------------------

    def state(self):
        try:
            settings = self._settings()
        except config.ConfigError as exc:
            # a hand edit gone wrong: say where, so the page can show it instead of a 500
            raise ApiError(
                422, "Invalid tc002.toml", f"{exc}. Fix the file, then reload this page."
            ) from None
        return {
            "night": self.app.night_status(),
            "config": {
                "path": str(self.config_path) if self.config_path else None,
                "shown": _home_relative(self.config_path),
                "data": config.to_data(settings),
                # sent back with a save (If-Match): a file changed since is not overwritten
                "version": self.app.config_version(),
            },
            "clock": self.app.clock_state(settings),
            "integrations": self.app.integrations(),
            "agents": self.agents.snapshot(),
            "freshness": freshness.read(),
            "focus": self.app.focus_now(),
            "connections": self._connections(),
            "staleAfter": {"age": stale.STALE_AFTER, "noData": stale.NO_DATA_AFTER},
            "catalogue": [
                {"key": k, "category": b.category, "index": b.index}
                for k, b in builtins.CATALOGUE.items()
            ],
            "screens": list(SCREENS),
            "screenOptions": screen_options.describe(SCREENS),
            "liveScreens": sorted(LIVE_SCREENS),
            "networked": sorted(NETWORKED),
            "games": {name: list(g.KEYS) for name, g in GAMES.items()},
            "schema": device_settings.schema(),
            "colors": message.COLORS,
            "alertKinds": list(message.ICONS),
            "messageMaxChars": message.MAX_CHARS,
            "limits": {"warn": usage_screen.WARN, "critical": usage_screen.CRITICAL},
            "slotSeconds": {"min": config.MIN_SLOT_SECONDS, "max": config.MAX_SLOT_SECONDS},
            "presets": presets.describe(),
            "ledThemes": themes.names(),
            "minFirmware": ".".join(map(str, MIN_FIRMWARE)),
            "timezones": device_settings.TIMEZONES,
        }

    def agents_now(self, query=None):
        return self.agents.snapshot()

    def appearance(self, body):
        """Change only the [appearance] table: LED theme and the UI palette it may follow."""
        return self.app.set_appearance(body.get("led_theme"), body.get("ui_palette"))

    def led(self):
        """Pixel fonts and LED palette, so browser previews draw exactly what the clock would."""
        return {
            "font": {"big": font.BIG, "small": font.SMALL},
            "palette": hex_palette(),
            "size": {"width": WIDTH, "height": HEIGHT},
        }

    def cities(self, query):
        return cities.search(query.get("q", ""), query.get("lang", "en"))

    # -- writes -------------------------------------------------------------------

    def save_config(self, data, restart=True, expected=None):
        """Validate, write, apply, restart; `expected` is the version the page loaded."""
        return self.app.save_config(data, restart, expected)

    def quick(self, body):
        """Quick settings (brightness, volume, …): merged into the saved tc002.toml and applied
        at once, leaving any unsaved draft in the UI alone."""
        patch = body.get("display")
        if not isinstance(patch, dict) or not patch:
            raise ApiError(422, "Nothing to change", 'Send {"display": {...}}.')
        return self.app.set_display(patch)

    def apply_preset(self, body):
        """The draft with a preset's rotation applied; the UI decides when to save it."""
        try:
            return {"data": presets.apply(body.get("data") or {}, body.get("preset"))}
        except ValueError as exc:
            raise ApiError(422, "Unknown preset", str(exc)) from None

    def live(self, body):
        return self.app.live(body.get("data"), body.get("focus") or None)

    def live_stop(self, body):
        return self.app.live_stop()

    def night(self, body):
        """Screen off now (`{"off": true, "until": "morning" | null}`) or on (`{"off": false}`)."""
        if body.get("off"):
            return self.app.screen_off(until_morning=body.get("until") == "morning")
        return self.app.screen_on()

    def show(self, body):
        return self.app.show(body.get("screen"), body.get("builtin"))

    def send_message(self, body):
        """Text or alert, played in the background so the request returns at once."""
        return self.app.play_message(
            body.get("text"), body.get("type"), body.get("kind", "done"), body.get("color")
        )


def _home_relative(path):
    """The config path as the sidebar shows it: ~/… rather than the user's home directory."""
    if not path:
        return None
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home) :] if text.startswith(home + "/") else text
