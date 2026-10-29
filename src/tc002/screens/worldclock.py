"""The time in two places, each with a three-letter tag.

Layout (52x16): two rows (y 0 and y 8), each a 3x5 tag (LDN), the time in the 5x7 font
and, when the date differs from here, +1 or -1. The colons blink.
"""

import datetime as dt
from dataclasses import dataclass
from typing import ClassVar
from zoneinfo import ZoneInfo

from ..render.anim import Animation
from ..render.canvas import Canvas
from ..render.palette import LED

TIME_X, DAY_X = 15, 45


def tag(zone):
    """Europe/London -> LON, America/New_York -> NEW: three letters from the city."""
    city = zone.rsplit("/", 1)[-1].replace("_", "")
    return city[:3].upper()


@dataclass(frozen=True)
class State:
    rows: tuple[tuple[str, str, int], ...]  # (tag, "HH MM", day offset from here)


class WorldClockScreen:
    APP = "worldclock"
    TICK = 20.0
    OPTIONS: ClassVar[dict] = {"zones": ("zones", ["Europe/London", "America/New_York"], 2)}

    def __init__(self, options=None, clock=None):
        self.zones = (options or {}).get("zones") or self.OPTIONS["zones"][1]
        self.clock = clock or (lambda: dt.datetime.now().astimezone())

    def sample(self):
        here = self.clock()
        rows = []
        for zone in self.zones:
            there = here.astimezone(ZoneInfo(zone))
            rows.append((tag(zone), there.strftime("%H %M"), (there.date() - here.date()).days))
        return State(tuple(rows))

    def render(self, state):
        frames = []
        for colon in (True, False):
            c = Canvas()
            for (label, hhmm, days), y in zip(state.rows, (0, 8), strict=False):
                c.text(1, y + 1, label, LED["label"], big=False)
                hh, mm = hhmm.split()
                x = c.text(TIME_X, y, hh, LED["white"]) + 1  # fixed slots: a blink never shifts
                if colon:
                    c.text(x, y, ":", LED["white"])
                c.text(x + 3, y, mm, LED["white"])
                if days:
                    c.text(DAY_X, y + 1, f"{days:+d}", LED["amber"], big=False)
            frames.append(c)
        return Animation(frames, 500, key=state)
