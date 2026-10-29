"""Tonight's moon: its phase drawn as a disc, its name and how much of it is lit.

Phase from the mean synodic month counted from a known new moon (2000-01-06 18:14 UTC);
good to within about a day, which is all a 13-pixel moon can show.

Layout (52x16): a 13x13 disc at the left, lit on the right while waxing and on the left
while waning (as seen from the northern hemisphere); the phase name and "nn% LIT" to its
right.
"""

import datetime as dt
import math
from dataclasses import dataclass

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


class MoonScreen:
    APP = "moon"
    TICK = 3600.0

    def __init__(self, options=None, clock=None):
        self.clock = clock or (lambda: dt.datetime.now(dt.UTC))

    def sample(self):
        p = phase(self.clock())
        return State(
            round(p * 8) % 8, round(p, 2), round((1 - math.cos(2 * math.pi * p)) / 2 * 100)
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
                c.set(DISC_X + px, DISC_Y + py, LED["soft_white"] if lit else LED["dim"])
        c.text(TEXT_X, 2, NAMES[state.eighth], LED["white"], big=False)
        c.text(TEXT_X, 9, f"{state.lit}% LIT", LED["label"], big=False)
        return Animation.still(c, key=state)
