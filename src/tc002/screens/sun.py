"""Sunrise and sunset where you are, and how far through the daylight it is now.

The place comes from the weather app's city (its latitude and longitude). Times use the
NOAA solar position formulas, accurate to about a minute.

Layout (52x16): a sun at the left; UP hh:mm and DN hh:mm stacked to its right; along the
bottom row, a line that fills from sunrise to sunset.
"""

import datetime as dt
import math
from dataclasses import dataclass

from ..render.anim import Animation
from ..render.canvas import WIDTH, Canvas
from ..render.palette import LED

SUN = ["...#...", ".#.#.#.", "..###..", "#######", "..###..", ".#.#.#.", "...#..."]
TEXT_X, BAR_X = 11, 11


def sun_times(day, lat, lon, tz):
    """(sunrise, sunset) as aware datetimes in `tz`; None for polar day or night."""
    n = day.timetuple().tm_yday
    gamma = 2 * math.pi / 365 * (n - 1)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    phi = math.radians(lat)
    cos_ha = math.cos(math.radians(90.833)) / (math.cos(phi) * math.cos(decl)) - math.tan(
        phi
    ) * math.tan(decl)
    if not -1 <= cos_ha <= 1:
        return None
    ha = math.degrees(math.acos(cos_ha))
    midnight = dt.datetime.combine(day, dt.time(), tzinfo=dt.UTC)

    def at(minutes):
        return (midnight + dt.timedelta(minutes=minutes)).astimezone(tz)

    return at(720 - 4 * (lon + ha) - eqtime), at(720 - 4 * (lon - ha) - eqtime)


@dataclass(frozen=True)
class State:
    rise: str | None  # "HH:MM", None when unknown or polar
    set: str | None
    daylight: int = 0  # % of today's daylight gone


class SunScreen:
    APP = "sun"
    TICK = 60.0
    # no options of its own: the place is the weather app's city (screens.build)

    def __init__(self, options=None, clock=None):
        options = options or {}
        self.lat, self.lon = options.get("lat"), options.get("lon")
        self.clock = clock or (lambda: dt.datetime.now().astimezone())

    def sample(self):
        if self.lat is None or self.lon is None:
            return State(None, None)
        now = self.clock()
        times = sun_times(now.date(), float(self.lat), float(self.lon), now.tzinfo)
        if times is None:
            return State(None, None)
        rise, sunset = times
        span = (sunset - rise).total_seconds()
        gone = min(1.0, max(0.0, (now - rise).total_seconds() / span)) if span > 0 else 0
        return State(rise.strftime("%H:%M"), sunset.strftime("%H:%M"), round(gone * 100))

    def render(self, state):
        c = Canvas()
        c.sprite(1, 3, SUN, LED["yellow"])
        if state.rise is None:
            c.text(TEXT_X, 2, "SET A", LED["label"], big=False)
            c.text(TEXT_X, 9, "CITY", LED["label"], big=False)
            return Animation.still(c, key=state)
        c.text(TEXT_X, 1, "UP", LED["label"], big=False)
        c.text(TEXT_X + 10, 1, state.rise, LED["amber"], big=False)
        c.text(TEXT_X, 8, "DN", LED["label"], big=False)
        c.text(TEXT_X + 10, 8, state.set, LED["orange"], big=False)
        width = WIDTH - BAR_X - 1
        c.rect(BAR_X, 14, width, 1, LED["track"])
        c.rect(BAR_X, 14, max(1, round(width * state.daylight / 100)), 1, LED["yellow"])
        return Animation.still(c, key=state)
