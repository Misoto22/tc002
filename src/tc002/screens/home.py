"""Values from Home Assistant: up to two entities, each a short name and its state.

Data: your Home Assistant's REST API, at the address in tc002.toml
[connections.homeassistant] with a long-lived access token from the Keychain.
"""

from dataclasses import dataclass
from typing import ClassVar

from .. import connections, net
from ..render import font
from ..render.anim import Animation
from ..render.canvas import WIDTH, Canvas
from ..render.palette import LED


@dataclass(frozen=True)
class State:
    rows: tuple[tuple[str, str], ...]  # (name, value with unit)
    connected: bool = True


class HomeScreen:
    APP = "home"
    TICK = 60.0
    OPTIONS: ClassVar[dict] = {"entities": ("list", ["sensor.living_room_temperature"], 2)}

    def __init__(self, options=None, settings=None, get=net.get_json):
        self.entities = (options or {}).get("entities") or []
        self.settings, self.get = settings, get

    def sample(self):
        url = connections.value(self.settings, "homeassistant", "url")
        token = connections.value(self.settings, "homeassistant", "token")
        if not url or not token:
            return State((), connected=False)
        rows = []
        for entity in self.entities:
            data = self.get(
                f"{url.rstrip('/')}/api/states/{entity}", {"Authorization": f"Bearer {token}"}
            )
            attrs = data.get("attributes", {})
            name = str(attrs.get("friendly_name") or entity.split(".")[-1]).upper()
            unit = attrs.get("unit_of_measurement") or ""
            rows.append((name, f"{data.get('state', '?')}{unit}".upper()))
        return State(tuple(rows))

    def render(self, state):
        c = Canvas()
        if not state.connected:
            c.text(1, 2, "HOME", LED["label"], big=False)
            c.text(1, 9, "CONNECT", LED["gray"], big=False)
            return Animation.still(c, key=state)
        for (name, value), y in zip(state.rows, (1, 9), strict=False):
            value = value[:6]
            room = WIDTH - font.text_width(font.SMALL, value) - 3
            c.text(1, y, name[: max(1, room // 4)], LED["label"], big=False)
            c.text(WIDTH - font.text_width(font.SMALL, value), y, value, LED["white"], big=False)
        return Animation.still(c, key=state)
