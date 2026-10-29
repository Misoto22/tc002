"""Crypto prices: up to two trading pairs, with the change since 24 hours ago.

Data: Coinbase Exchange's public product stats (no key). Each row: the coin, its price
(shortened to fit: 79.8K), and the 24-hour change, green up and red down.
"""

from dataclasses import dataclass
from typing import ClassVar

from .. import net
from ..render import font
from ..render.anim import Animation
from ..render.canvas import WIDTH, Canvas
from ..render.palette import LED

URL = "https://api.exchange.coinbase.com/products/{pair}/stats"


def short_price(p):
    if p >= 10000:
        return f"{p / 1000:.1f}K" if p < 100000 else f"{p / 1000:.0f}K"
    return f"{p:.0f}" if p >= 100 else f"{p:.2f}"


@dataclass(frozen=True)
class State:
    rows: tuple[tuple[str, str, float], ...]  # (coin, price text, % change)


class CryptoScreen:
    APP = "crypto"
    TICK = 120.0
    OPTIONS: ClassVar[dict] = {"pairs": ("list", ["BTC-USD", "ETH-USD"], 2)}

    def __init__(self, options=None, get=net.get_json):
        self.pairs = (options or {}).get("pairs") or self.OPTIONS["pairs"][1]
        self.get = get

    def sample(self):
        rows = []
        for pair in self.pairs:
            stats = self.get(URL.format(pair=pair))
            last, opened = float(stats["last"]), float(stats["open"])
            change = (last - opened) / opened * 100 if opened else 0
            rows.append((pair.split("-")[0][:4], short_price(last), round(change, 1)))
        return State(tuple(rows))

    def render(self, state):
        c = Canvas()
        for (coin, price, change), y in zip(state.rows, (1, 9), strict=False):
            c.text(1, y, coin, LED["label"], big=False)
            c.text(18, y, price, LED["white"], big=False)
            text = f"{change:+.1f}".replace("+", "")
            c.text(
                WIDTH - font.text_width(font.SMALL, text),
                y,
                text,
                LED["green"] if change >= 0 else LED["red"],
                big=False,
            )
        return Animation.still(c, key=state)
