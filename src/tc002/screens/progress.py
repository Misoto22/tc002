"""How much of today, this week and this year has gone: three bars.

Layout (52x16), one row per period at y 0, 5 and 10:
  x 1-3   D / W / Y (small font, the bar's colour)
  x 6-37  the bar, 3 px tall, empty track behind it
  x 40-51 the percentage, right-aligned, in the bar's colour (rows touch: colour parts them)
"""

import datetime as dt
from dataclasses import dataclass
from typing import ClassVar

from ..render import font
from ..render.anim import Animation
from ..render.canvas import WIDTH, Canvas
from ..render.palette import LED

BAR_X, BAR_W = 6, 32
ROWS = (("D", "sky"), ("W", "violet"), ("Y", "amber"))


@dataclass(frozen=True)
class State:
    day: int
    week: int
    year: int


def fractions(now, week_start="monday"):
    """(day, week, year) gone at `now`, each 0..1."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day = (now - midnight).total_seconds() / 86400
    weekday = now.weekday() if week_start == "monday" else (now.weekday() + 1) % 7
    week = (weekday + day) / 7
    start = dt.datetime(now.year, 1, 1, tzinfo=now.tzinfo)
    length = (dt.datetime(now.year + 1, 1, 1, tzinfo=now.tzinfo) - start).total_seconds()
    return day, week, (now - start).total_seconds() / length


class ProgressScreen:
    APP = "progress"
    TICK = 60.0
    OPTIONS: ClassVar[dict] = {"week_start": ("choice", "monday", ["monday", "sunday"])}

    def __init__(self, options=None, clock=dt.datetime.now):
        self.week_start = (options or {}).get("week_start", "monday")
        self.clock = clock

    def sample(self):
        parts = fractions(self.clock().astimezone(), self.week_start)
        return State(*(min(100, int(p * 100)) for p in parts))

    def render(self, state):
        c = Canvas()
        for y, (letter, colour), pct in zip(
            (0, 5, 10), ROWS, (state.day, state.week, state.year), strict=True
        ):
            c.text(1, y, letter, LED[colour], big=False)
            c.rect(BAR_X, y + 1, BAR_W, 3, LED["track"])
            c.rect(BAR_X, y + 1, max(1, round(BAR_W * pct / 100)), 3, LED[colour])
            label = f"{pct}"
            # 3 rows of 5 px fill 15 of 16: no room for gaps, so each row keeps its own colour
            c.text(WIDTH - font.text_width(font.SMALL, label), y, label, LED[colour], big=False)
        return Animation.still(c, key=state)
