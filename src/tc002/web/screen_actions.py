"""API actions behind a screen's own page: try it with real data, find stock symbols,
list Home Assistant entities. Nothing here touches the clock.

Mixed into web.api.Api.
"""

import base64
import dataclasses
import subprocess
import time
import urllib.parse

from .. import net
from ..render import mockup
from ..screens import SCREENS, build
from ..screens import home as home_screen
from .errors import ApiError

SYMBOL_SEARCH = "https://query1.finance.yahoo.com/v1/finance/search"
MAX_FACTS = 8
FAILURES = (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError)


def facts(state, prefix=""):
    """What a screen read, as short label/value pairs for the UI (never secrets: screen
    states hold only what the clock would show)."""
    out = []
    if not dataclasses.is_dataclass(state):
        return out
    for field in dataclasses.fields(state):
        value = getattr(state, field.name)
        if dataclasses.is_dataclass(value):
            out += facts(value, f"{prefix}{field.name}.")
        elif isinstance(value, str | int | float | bool) or value is None:
            out.append([f"{prefix}{field.name}", "—" if value is None else str(value)[:60]])
        elif isinstance(value, tuple | list) and value and len(value) <= 6:
            out.append([f"{prefix}{field.name}", ", ".join(str(v)[:24] for v in value)])
    return out[:MAX_FACTS]


class ScreenActions:
    def try_screen(self, body):
        """Sample a screen now, with its saved options or the draft's, and return what it
        read, how long it took and the picture it would put on the clock."""
        name = body.get("screen")
        if name not in SCREENS:
            raise ApiError(422, "Unknown screen", f"No screen named {name!r}.")
        draft = body.get("options")
        started = time.monotonic()
        try:
            screen = build(
                name, self._settings_or_none(), draft if isinstance(draft, dict) else None
            )
            state = screen.sample()
            anim = screen.render(state)
        except FAILURES as exc:
            ms = round((time.monotonic() - started) * 1000)
            return {"ok": False, "error": str(exc)[:200] or type(exc).__name__, "ms": ms}
        gif = mockup.led_gif(anim, self._led_theme())
        return {
            "ok": True,
            "ms": round((time.monotonic() - started) * 1000),
            "facts": facts(state),
            "gif": "data:image/gif;base64," + base64.b64encode(gif).decode(),
        }

    def symbols(self, query):
        """Stocks, indices and funds matching a name or ticker, from Yahoo Finance."""
        q = (query.get("q") or "").strip()[:40]
        if not q:
            return {"results": []}
        url = (
            f"{SYMBOL_SEARCH}?{urllib.parse.urlencode({'q': q, 'quotesCount': 8, 'newsCount': 0})}"
        )
        try:
            quotes = net.get_json(url).get("quotes") or []
        except (OSError, ValueError) as exc:
            raise ApiError(502, "Search failed", str(exc)[:200]) from None
        return {
            "results": [
                {
                    "symbol": r["symbol"],
                    "name": r.get("shortname") or r.get("longname") or "",
                    "exchange": r.get("exchDisp") or r.get("exchange") or "",
                    "type": (r.get("quoteType") or "").lower(),
                }
                for r in quotes
                if r.get("symbol")
                and r.get("quoteType") in ("EQUITY", "ETF", "INDEX", "MUTUALFUND", "CRYPTOCURRENCY")
            ]
        }

    def home_entities(self, query):
        """The user's Home Assistant entities worth showing, for the picker."""
        screen = home_screen.HomeScreen(settings=self._settings_or_none())
        try:
            states = screen.all_states()
        except (OSError, ValueError) as exc:
            raise ApiError(502, "Home Assistant unreachable", str(exc)[:200]) from None
        if states is None:
            raise ApiError(409, "Not connected", "Add the address and token in Connections first.")
        return {"results": home_screen.entity_list(states)}
