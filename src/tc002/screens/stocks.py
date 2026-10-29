"""One stock or index: its price, today's change, and today's chart.

Data: Yahoo Finance's chart endpoint (no key; unofficial, so it may change). Top row:
the symbol, the price and the change since yesterday's close; below, today's prices as
a 52-column area chart, green above yesterday's close and red below.
"""

from dataclasses import dataclass
from typing import ClassVar

from .. import net
from ..render import font
from ..render.anim import Animation
from ..render.canvas import HEIGHT, WIDTH, Canvas, dim
from ..render.palette import LED

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=5m"
CHART_TOP = 7


@dataclass(frozen=True)
class State:
    symbol: str
    price: float
    change: float  # %
    points: tuple[float, ...]  # closes, oldest first
    previous: float


class StocksScreen:
    APP = "stocks"
    TICK = 300.0
    OPTIONS: ClassVar[dict] = {"symbol": ("text", "AAPL", 10)}

    def __init__(self, options=None, get=net.get_json):
        self.symbol = ((options or {}).get("symbol") or "AAPL").upper()
        self.get = get

    def sample(self):
        result = self.get(URL.format(symbol=self.symbol))["chart"]["result"][0]
        meta = result["meta"]
        closes = [p for p in result["indicators"]["quote"][0]["close"] if p is not None]
        previous = meta.get("chartPreviousClose") or meta.get("previousClose") or closes[0]
        price = meta["regularMarketPrice"]
        return State(
            self.symbol,
            round(price, 2),
            round((price - previous) / previous * 100, 2),
            tuple(closes),
            previous,
        )

    def render(self, state):
        c = Canvas()
        up = state.change >= 0
        c.text(1, 0, state.symbol[:5], LED["label"], big=False)
        price = f"{state.price:.0f}" if state.price >= 1000 else f"{state.price:.2f}"
        c.text(23, 0, price, LED["white"], big=False)
        change = f"{state.change:+.1f}".replace("+", "")
        c.text(
            WIDTH - font.text_width(font.SMALL, change),
            0,
            change,
            LED["green"] if up else LED["red"],
            big=False,
        )
        pts = state.points or (state.previous,)
        lo, hi = min(*pts, state.previous), max(*pts, state.previous)
        span = (hi - lo) or 1
        rows = HEIGHT - CHART_TOP

        def y_of(v):
            return CHART_TOP + rows - 1 - round((v - lo) / span * (rows - 1))

        base = y_of(state.previous)
        for x in range(WIDTH):
            v = pts[min(len(pts) - 1, x * len(pts) // WIDTH)]
            y = y_of(v)
            colour = LED["green"] if v >= state.previous else LED["red"]
            for yy in range(min(y, base), max(y, base) + 1):
                c.set(x, yy, dim(colour, 0.35))
            c.set(x, y, colour)
        return Animation.still(c, key=state)
