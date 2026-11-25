"""Use cases that draw or look things up for the settings UI, without changing anything:
LED previews, trying a screen with real data, and the pickers' searches."""

import base64
import dataclasses
import subprocess
import threading
import time
from functools import lru_cache

from ..clock import builtins
from ..games import GAMES
from ..games.demo import demo
from ..lookup import cities, symbols
from ..render import mockup, themes
from ..screens import SCREENS, build, builtin_previews, message
from ..screens import home as home_screen
from ..screens.examples import examples
from . import catalog
from .errors import Conflict, InvalidRequest, NotFound, ServiceUnavailable

MAX_FACTS = 8
FAILURES = (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError)
HIDDEN = {"index", "count", "connected", "key", "closes", "phase"}  # paging and drawing data


class Content:
    # -- previews -------------------------------------------------------------------

    def preview(self, name, theme=None, text=None, color=None, kind=None):
        """LED mock-up GIF bytes for an example screen, a built-in app, a game demo, a
        live screen (`live-<name>`) or a message draft (`text`, `alert`).

        Screens are drawn in the saved LED theme, or in `theme` (a draft not yet saved);
        messages keep the colour they were given."""
        theme = theme if theme in themes.THEMES else self.led_theme()
        if name == "text":
            texts = message.text_animation(
                (text or "TEXT")[: catalog.MESSAGE_MAX_CHARS], color or "white"
            )
            return mockup.led_gif(texts[0], themes.CLASSIC)
        if name == "alert":
            anim = message.alert_animation(
                (text or "DONE")[: catalog.ALERT_MAX_CHARS], kind or "done", color
            )
            return mockup.led_gif(anim, themes.CLASSIC)
        if name.startswith("live-") and name.removeprefix("live-") in catalog.LIVE_SCREENS:
            screen = build(name.removeprefix("live-"), self.settings_or_none())
            return mockup.led_gif(screen.render(screen.sample()), theme)
        gif = _fixed(name, theme)
        if gif is None:
            raise NotFound("Unknown preview", f"No preview named {name!r}.")
        return gif

    def warm_previews(self):
        """Draw every fixed preview in the saved theme once, in the background, so the
        UI's first pictures are ready. One warm-up at a time per process."""
        threading.Thread(target=_warm, args=(self.led_theme(),), daemon=True).start()

    # -- trying screens ---------------------------------------------------------------

    def try_screen(self, name, options=None):
        """Sample a screen now, with its saved options or `options` (a draft), and return
        what it read, how long it took and the picture it would put on the clock."""
        if name not in SCREENS:
            raise InvalidRequest("Unknown screen", f"No screen named {name!r}.")
        started = time.monotonic()
        try:
            screen = build(
                name, self.settings_or_none(), options if isinstance(options, dict) else None
            )
            state = screen.sample()
            anim = screen.render(state)
        except FAILURES as exc:
            ms = round((time.monotonic() - started) * 1000)
            return {"ok": False, "error": str(exc)[:200] or type(exc).__name__, "ms": ms}
        gif = mockup.led_gif(anim, self.led_theme())
        return {
            "ok": True,
            "ms": round((time.monotonic() - started) * 1000),
            "facts": facts(state),
            "gif": "data:image/gif;base64," + base64.b64encode(gif).decode(),
        }

    # -- the pickers' searches --------------------------------------------------------

    def find_cities(self, query, lang="en"):
        return cities.search(query or "", lang or "en")

    def find_symbols(self, query):
        """Stocks, indices and funds matching a name or ticker."""
        try:
            return {"results": symbols.search(query)}
        except (OSError, ValueError) as exc:
            raise ServiceUnavailable("Search failed", str(exc)[:200]) from None

    def home_entities(self):
        """The user's Home Assistant entities worth showing, for the picker."""
        screen = home_screen.HomeScreen(settings=self.settings_or_none())
        try:
            states = screen.all_states()
        except (OSError, ValueError) as exc:
            raise ServiceUnavailable("Home Assistant unreachable", str(exc)[:200]) from None
        if states is None:
            raise Conflict("Not connected", "Add the address and token in Connections first.")
        return {"results": home_screen.entity_list(states)}


def facts(state):
    """What a screen read, as short label/value pairs (never secrets: screen states hold
    only what the clock would show). Nested values are flattened, so a stock reads
    "symbol, price, change", not "quote.symbol"."""
    out = []
    if not dataclasses.is_dataclass(state):
        return out
    for field in dataclasses.fields(state):
        value = getattr(state, field.name)
        label = field.name.replace("_", " ")
        if field.name in HIDDEN:
            continue
        if dataclasses.is_dataclass(value):
            out += facts(value)
        elif isinstance(value, str | int | float | bool) or value is None:
            out.append([label, "—" if value is None else str(value)[:60]])
        elif isinstance(value, tuple | list) and value and len(value) <= 6:
            out.append([label, ", ".join(str(v)[:24] for v in value)])
    return out[:MAX_FACTS]


_warming = threading.Lock()


def _warm(theme):
    if not _warming.acquire(blocking=False):
        return
    try:
        names = [
            *_examples(),
            *(f"builtin-{k}" for k in builtins.CATALOGUE),
            *(f"game-{g}" for g in GAMES),
        ]
        for name in names:
            _fixed(name, theme)
    finally:
        _warming.release()


@lru_cache(maxsize=1)
def _examples():
    return examples()


@lru_cache(maxsize=512)
def _fixed(name, theme):
    """GIF bytes of an example screen, a built-in app or a game demo; None if unknown."""
    if name.startswith("game-") and name.removeprefix("game-") in GAMES:
        anim = demo(name.removeprefix("game-"))
    elif name.startswith("builtin-"):
        try:
            anim = builtin_previews.render(name.removeprefix("builtin-"))
        except ValueError:
            return None
    elif name in _examples():
        anim = _examples()[name]
    else:
        return None
    return mockup.led_gif(anim, theme)
