"""Days left until a date you choose, with your label for it.

Layout (52x16): more than a day away, the number of days large at the left with DAYS
beside it; on the day itself, the hours and minutes left. The label sits on the bottom
row. With no date set it says so.
"""

import datetime as dt
from dataclasses import dataclass
from typing import ClassVar

from ..render import font
from ..render.anim import Animation
from ..render.canvas import Canvas
from ..render.palette import LED


@dataclass(frozen=True)
class State:
    days: int | None  # None: no date set
    minutes: int = 0  # left today, when days == 0
    label: str = ""


class CountdownScreen:
    APP = "countdown"
    TICK = 60.0
    OPTIONS: ClassVar[dict] = {"date": ("date", "", None), "label": ("text", "", 10)}

    def __init__(self, options=None, clock=dt.datetime.now):
        options = options or {}
        self.date = dt.date.fromisoformat(options["date"]) if options.get("date") else None
        self.label, self.clock = options.get("label", "").upper(), clock

    def sample(self):
        if self.date is None:
            return State(None)
        now = self.clock()
        target = dt.datetime.combine(self.date, dt.time())
        left = max(0, (target - now).total_seconds())
        return State(int(left // 86400), int(left % 86400 // 60), self.label)

    def render(self, state):
        c = Canvas()
        if state.days is None:
            c.text_centered(2, "SET A", LED["label"], big=False)
            c.text_centered(9, "DATE", LED["label"], big=False)
            return Animation.still(c, key=state)
        if state.days >= 1:
            x = c.text(1, 1, str(min(state.days, 9999)), LED["white"]) + 2
            c.text(x, 3, "DAY" if state.days == 1 else "DAYS", LED["amber"], big=False)
        else:
            c.text(1, 1, f"{state.minutes // 60:02d}:{state.minutes % 60:02d}", LED["amber"])
        label = state.label or "TO GO"
        if font.text_width(font.SMALL, label) <= 50:
            c.text(1, 10, label, LED["label"], big=False)
        return Animation.still(c, key=state)
