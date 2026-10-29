"""Air quality where your weather city is: the European AQI, coloured by band, and PM2.5.

Data: Open-Meteo's air quality API (free, no key; non-commercial use). Bands follow
the European AQI: good, fair, moderate, poor, very poor, extremely poor.
"""

from dataclasses import dataclass

from .. import net
from ..render.anim import Animation
from ..render.canvas import Canvas
from ..render.palette import LED

URL = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=european_aqi,pm2_5"
BANDS = ((20, "green"), (40, "teal"), (60, "yellow"), (80, "amber"), (100, "red"), (999, "violet"))


@dataclass(frozen=True)
class State:
    aqi: int | None
    pm25: float | None = None


def band(aqi):
    return next(colour for limit, colour in BANDS if aqi <= limit)


class AirScreen:
    APP = "air"
    TICK = 900.0

    def __init__(self, options=None, get=net.get_json):
        options = options or {}
        self.lat, self.lon, self.get = options.get("lat"), options.get("lon"), get

    def sample(self):
        if self.lat is None or self.lon is None:
            return State(None)
        now = self.get(URL.format(lat=self.lat, lon=self.lon))["current"]
        return State(round(now["european_aqi"]), round(now["pm2_5"], 1))

    def render(self, state):
        c = Canvas()
        c.text(1, 1, "AQI", LED["label"], big=False)
        if state.aqi is None:
            c.text(1, 9, "SET A CITY", LED["label"], big=False)
            return Animation.still(c, key=state)
        c.text(16, 1, str(state.aqi), LED[band(state.aqi)])
        c.text(1, 10, f"PM2.5 {state.pm25:g}", LED["soft_white"], big=False)
        return Animation.still(c, key=state)
