"""Stocks and indices: each one's price, today's change and today's chart, in turn.

Data: Yahoo Finance's chart endpoint (no key; unofficial, so it may change). The symbols
are fetched together every `refresh` minutes and shown one at a time for `seconds`
each (pager.py). Top row: the symbol, the price and the change since yesterday's close,
laid out from the right so they never overlap; below, today's prices as a 52-column
area chart, green above yesterday's close and red below. With several symbols, a dot
per symbol on the bottom row marks which one this is.
"""

from dataclasses import dataclass
from typing import ClassVar

from .. import net
from ..render import font
from ..render.anim import Animation
from ..render.canvas import HEIGHT, WIDTH, Canvas, dim
from ..render.palette import LED
from .pager import Pager

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m"
CHART_TOP = 7
GAP = 3  # pixels between the symbol, the price and the change


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    change: float  # %
    points: tuple[float, ...]  # closes, oldest first
    previous: float


@dataclass(frozen=True)
class State:
    quote: Quote
    index: int = 0
    count: int = 1


def price_text(price, room):
    """The price in at most `room` pixels: cents while they fit, then whole units."""
    for text in (f"{price:.2f}", f"{price:.0f}"):
        if font.text_width(font.SMALL, text) <= room:
            return text
    return f"{price / 1000:.0f}K"


def fetch_quote(get, symbol):
    result = get(URL.format(symbol=symbol))["chart"]["result"][0]
    meta = result["meta"]
    closes = [p for p in result["indicators"]["quote"][0]["close"] if p is not None]
    price = meta["regularMarketPrice"]
    previous = meta.get("chartPreviousClose") or meta.get("previousClose") or closes[0]
    change = round((price - previous) / previous * 100, 2)
    return Quote(symbol, round(price, 2), change, tuple(closes), previous)


class StocksScreen:
    APP = "stocks"
    OPTIONS: ClassVar[dict] = {
        "symbols": ("symbols", ["AAPL"], 4),
        "refresh": ("int", 5, (1, 60)),  # minutes between fetches
        "seconds": ("int", 8, (4, 60)),  # each symbol on screen
    }

    def __init__(self, options=None, get=net.get_json, clock=None):
        options = options or {}
        symbols = options.get("symbols") or [options.get("symbol") or "AAPL"]
        self.symbols = [s.upper() for s in symbols]
        self.get = get
        seconds = options.get("seconds", 8)
        self.TICK = float(min(seconds, 15))
        kwargs = {"clock": clock} if clock else {}
        self.pager = Pager(self._fetch, options.get("refresh", 5) * 60, seconds, **kwargs)

    def _fetch(self):
        return [fetch_quote(self.get, s) for s in self.symbols]

    def sample(self):
        index, count, quote = self.pager.current()
        return State(quote, index, count)

    def render(self, state):
        q = state.quote
        c = Canvas()
        up = q.change >= 0
        change = f"{q.change:+.1f}".replace("+", "")
        change_x = WIDTH - font.text_width(font.SMALL, change)
        symbol = q.symbol.split(".")[0][:5]
        symbol_end = 1 + font.text_width(font.SMALL, symbol)
        price = price_text(q.price, change_x - GAP - symbol_end - GAP)
        price_x = change_x - GAP - font.text_width(font.SMALL, price)
        c.text(1, 0, symbol, LED["label"], big=False)
        c.text(price_x, 0, price, LED["white"], big=False)
        c.text(change_x, 0, change, LED["green"] if up else LED["red"], big=False)
        _chart(c, q, bottom=HEIGHT - (2 if state.count > 1 else 0))
        if state.count > 1:
            for i in range(state.count):
                c.set(
                    WIDTH // 2 - state.count + i * 2,
                    HEIGHT - 1,
                    LED["white"] if i == state.index else LED["gray"],
                )
        return Animation.still(c, key=state)


def _chart(c, q, bottom):
    pts = q.points or (q.previous,)
    lo, hi = min(*pts, q.previous), max(*pts, q.previous)
    span = (hi - lo) or 1
    rows = bottom - CHART_TOP

    def y_of(v):
        return CHART_TOP + rows - 1 - round((v - lo) / span * (rows - 1))

    base = y_of(q.previous)
    for x in range(WIDTH):
        v = pts[min(len(pts) - 1, x * len(pts) // WIDTH)]
        y = y_of(v)
        colour = LED["green"] if v >= q.previous else LED["red"]
        for yy in range(min(y, base), max(y, base) + 1):
            c.set(x, yy, dim(colour, 0.35))
        c.set(x, y, colour)
