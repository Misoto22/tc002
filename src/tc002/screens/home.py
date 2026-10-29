"""Values from Home Assistant, one entity at a time: its name, then its value large.

Data: your Home Assistant's REST API, at the address in tc002.toml
[connections.homeassistant] with a long-lived access token from the Keychain. All states
are read in one call (GET /api/states) every `refresh` minutes and the chosen entities
are shown in turn (pager.py), `seconds` each.

How a state reads on 16 rows, following what desk displays for Home Assistant settled
on: numbers rounded (one decimal for temperatures, none otherwise) with their unit;
doors and windows OPEN or SHUT, motion MOTION or CLEAR, people HOME or AWAY, switches
and lights ON or OFF in a colour; "unavailable" as "--".
"""

from dataclasses import dataclass
from typing import ClassVar

from .. import connections, net
from ..render import font
from ..render.anim import Animation
from ..render.canvas import WIDTH, Canvas
from ..render.palette import LED
from .pager import Pager

PICKABLE = (
    "sensor",
    "binary_sensor",
    "climate",
    "person",
    "light",
    "switch",
    "weather",
    "alarm_control_panel",
    "media_player",
    "input_boolean",
    "lock",
    "cover",
)
OPENINGS = {"door", "window", "opening", "garage_door"}
MOTION = {"motion", "occupancy", "presence"}


@dataclass(frozen=True)
class Value:
    name: str
    text: str
    colour: str = "white"


@dataclass(frozen=True)
class State:
    value: Value | None
    index: int = 0
    count: int = 0
    connected: bool = True


def entity_list(states):
    """For the UI's picker: entities worth showing, as {id, name, domain, value}."""
    out = []
    for s in states:
        domain = s["entity_id"].split(".")[0]
        if domain not in PICKABLE:
            continue
        v = describe(s)
        out.append({"id": s["entity_id"], "name": friendly(s), "domain": domain, "value": v.text})
    return sorted(out, key=lambda e: (PICKABLE.index(e["domain"]), e["name"].casefold()))


def friendly(s):
    return str(s.get("attributes", {}).get("friendly_name") or s["entity_id"].split(".")[-1])


def describe(s):
    """A state as the clock shows it: short text and a colour."""
    domain = s["entity_id"].split(".")[0]
    state = str(s.get("state", ""))
    attrs = s.get("attributes", {})
    cls = attrs.get("device_class")
    if state in ("unavailable", "unknown", ""):
        return Value("", "--", "gray")
    if domain == "binary_sensor":
        on = state == "on"
        if cls in OPENINGS:
            return Value("", "OPEN" if on else "SHUT", "amber" if on else "green")
        if cls in MOTION:
            return Value("", "MOTION" if on else "CLEAR", "amber" if on else "label")
        return Value("", "ON" if on else "OFF", "green" if on else "gray")
    if domain == "person":
        home = state == "home"
        return Value("", "HOME" if home else "AWAY", "green" if home else "label")
    if domain in ("light", "switch", "input_boolean"):
        return Value("", state.upper(), "yellow" if state == "on" else "gray")
    if domain == "climate":
        now, target = attrs.get("current_temperature"), attrs.get("temperature")
        return Value("", f"{_num(now, 1)}>{_num(target, 1)}" if target else _num(now, 1))
    try:
        number = float(state)
    except ValueError:
        return Value("", state.upper().replace("_", " "))
    unit = str(attrs.get("unit_of_measurement") or "").replace("°", "")  # no ° in the font
    digits = 1 if cls == "temperature" or unit in ("C", "F") else 0
    return Value("", f"{_num(number, digits)}{unit}")


def _num(value, digits):
    try:
        return f"{float(value):.{digits}f}"
    except TypeError, ValueError:
        return "--"


class HomeScreen:
    APP = "home"
    OPTIONS: ClassVar[dict] = {
        "entities": ("entities", ["sensor.living_room_temperature"], 6),
        "refresh": ("int", 1, (1, 30)),  # minutes
        "seconds": ("int", 5, (3, 30)),  # each entity
    }

    def __init__(self, options=None, settings=None, get=net.get_json, clock=None):
        o = {k: d for k, (_, d, _) in self.OPTIONS.items()} | (options or {})
        self.entities = list(o["entities"])
        self.settings, self.get = settings, get
        self.TICK = float(min(o["seconds"], 15))
        kwargs = {"clock": clock} if clock else {}
        self.pager = Pager(self._fetch, o["refresh"] * 60, o["seconds"], **kwargs)

    def all_states(self):
        url = connections.value(self.settings, "homeassistant", "url")
        token = connections.value(self.settings, "homeassistant", "token")
        if not url or not token:
            return None
        return self.get(f"{url.rstrip('/')}/api/states", {"Authorization": f"Bearer {token}"})

    def _fetch(self):
        states = self.all_states()
        if states is None:
            return [None]
        by_id = {s["entity_id"]: s for s in states}
        out = []
        for entity in self.entities:
            s = by_id.get(entity)
            if s is None:
                out.append(Value(entity.split(".")[-1].upper(), "--", "gray"))
                continue
            v = describe(s)
            out.append(Value(friendly(s).upper(), v.text, v.colour))
        return out

    def sample(self):
        index, count, value = self.pager.current()
        if value is None:
            return State(None, connected=False)
        return State(value, index, count)

    def render(self, state):
        c = Canvas()
        if not state.connected or state.value is None:
            c.text(1, 2, "HOME", LED["label"], big=False)
            c.text(1, 9, "CONNECT", LED["gray"], big=False)
            return Animation.still(c, key=state)
        v = state.value
        room = WIDTH - 2 - (2 * state.count + 2 if state.count > 1 else 0)
        name = v.name
        while name and font.text_width(font.SMALL, name) > room:
            name = name[:-1]
        c.text(1, 0, name, LED["label"], big=False)
        table = font.BIG if font.text_width(font.BIG, v.text) <= WIDTH - 2 else font.SMALL
        y = 8 if table is font.BIG else 9
        c.text(1, y, v.text, LED[v.colour], big=table is font.BIG)
        if state.count > 1:
            for i in range(state.count):
                c.set(
                    WIDTH - 2 * state.count + i * 2,
                    1,
                    LED["white"] if i == state.index else LED["gray"],
                )
        return Animation.still(c, key=state)
