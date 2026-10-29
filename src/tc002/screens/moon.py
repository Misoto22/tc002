"""Tonight's moon: its phase drawn as a disc, its name and how much of it is lit.

Phase from the mean synodic month counted from a known new moon (2000-01-06 18:14 UTC);
good to within about a day, which is all a 13-pixel moon can show.

Layout (52x16): a 13x13 disc at the left, lit on the right while waxing and on the left
while waning as seen from the northern hemisphere (mirrored for the southern); the phase
name to its right, and under it how much is lit or how many days to the next full moon.
"""

import datetime as dt
import math
from dataclasses import dataclass
from typing import ClassVar

from ..render.anim import Animation
from ..render.canvas import Canvas
from ..render.palette import LED

SYNODIC_DAYS = 29.530588853
NEW_MOON = dt.datetime(2000, 1, 6, 18, 14, tzinfo=dt.UTC)
DISC, DISC_X, DISC_Y = 13, 1, 1
TEXT_X = 17
NAMES = ["NEW MOON", "WAX CRES", "1ST QTR", "WAX GIBB", "FULL", "WAN GIBB", "LAST QTR", "WAN CRES"]


def phase(when):
    """0..1 through the lunar month: 0 new, 0.25 first quarter, 0.5 full."""
    return ((when - NEW_MOON).total_seconds() / 86400 / SYNODIC_DAYS) % 1


@dataclass(frozen=True)
class State:
    eighth: int  # 0..7: which of the eight named phases
    phase: float  # rounded, for drawing
    lit: int  # % of the disc lit
    to_full: int = 0  # whole days to the next full moon


class MoonScreen:
    APP = "moon"
    TICK = 3600.0
    OPTIONS: ClassVar[dict] = {
        "hemisphere": ("choice", "north", ("north", "south")),
        "detail": ("choice", "lit", ("lit", "full")),  # second line: % lit, or days to full
    }

    def __init__(self, options=None, clock=None):
        o = options or {}
        self.south = o.get("hemisphere") == "south"
        self.detail = o.get("detail", "lit")
        self.clock = clock or (lambda: dt.datetime.now(dt.UTC))

    def sample(self):
        p = phase(self.clock())
        to_full = round(((0.5 - p) % 1) * SYNODIC_DAYS)
        return State(
            round(p * 8) % 8,
            round(p, 2),
            round((1 - math.cos(2 * math.pi * p)) / 2 * 100),
            to_full,
        )

    def render(self, state):
        c = Canvas()
        r = DISC / 2
        k = math.cos(2 * math.pi * state.phase)
        for py in range(DISC):
            for px in range(DISC):
                x, y = (px + 0.5 - r) / r, (py + 0.5 - r) / r
                if x * x + y * y > 1:
                    continue
                edge = k * math.sqrt(1 - y * y)
                lit = x > edge if state.phase < 0.5 else x < -edge
                col = DISC - 1 - px if self.south else px
                c.set(DISC_X + col, DISC_Y + py, LED["soft_white"] if lit else LED["dim"])
        c.text(TEXT_X, 2, NAMES[state.eighth], LED["white"], big=False)
        if self.detail == "full" and state.eighth != 4:
            c.text(TEXT_X, 9, f"FULL {state.to_full}D", LED["label"], big=False)
        else:
            c.text(TEXT_X, 9, f"{state.lit}% LIT", LED["label"], big=False)
        return Animation.still(c, key=state)
