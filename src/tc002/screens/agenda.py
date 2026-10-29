"""Your next calendar event: when it starts, how long until then, and its title.

Data: a calendar's private ICS link (Google, iCloud, Outlook and others offer one), kept
in the Keychain (connections.py). Events repeating daily or weekly (RRULE FREQ=DAILY or
WEEKLY, with INTERVAL, BYDAY, COUNT and UNTIL) are expanded; rarer rules show only
their first occurrence.
"""

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .. import connections, net
from ..render import font
from ..render.anim import Animation
from ..render.canvas import Canvas
from ..render.palette import LED
from . import ticker

DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
LOOKAHEAD = dt.timedelta(days=7)


def unfold(text):
    lines = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        elif raw:
            lines.append(raw)
    return lines


def _when(params, value, local):
    if "VALUE=DATE" in params or len(value) == 8:
        return dt.datetime.strptime(value[:8], "%Y%m%d").replace(tzinfo=local)
    stamp = dt.datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
    if value.endswith("Z"):
        return stamp.replace(tzinfo=dt.UTC)
    zone = next((p[5:] for p in params.split(";") if p.startswith("TZID=")), None)
    try:
        return stamp.replace(tzinfo=ZoneInfo(zone) if zone else local)
    except ZoneInfoNotFoundError, ValueError:
        return stamp.replace(tzinfo=local)


def events(text, local):
    """(start, summary, rrule dict) for each VEVENT."""
    out, cur = [], None
    for line in unfold(text):
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT" and cur is not None:
            if "start" in cur:
                out.append((cur["start"], cur.get("summary", ""), cur.get("rrule", {})))
            cur = None
        elif cur is not None and ":" in line:
            head, value = line.split(":", 1)
            name, _, params = head.partition(";")
            if name == "DTSTART":
                cur["start"] = _when(params, value, local)
            elif name == "SUMMARY":
                cur["summary"] = value.replace("\\,", ",").replace("\\n", " ").strip()
            elif name == "RRULE":
                cur["rrule"] = dict(p.split("=", 1) for p in value.split(";") if "=" in p)
    return out


def occurrences(start, rule, until):
    """Starts of an event up to `until`, for daily and weekly rules."""
    freq = rule.get("FREQ")
    if freq not in ("DAILY", "WEEKLY"):
        yield start
        return
    step = int(rule.get("INTERVAL", 1))
    count = int(rule["COUNT"]) if "COUNT" in rule else None
    end = _when("", rule["UNTIL"], start.tzinfo) if "UNTIL" in rule else until
    days = {DAYS.index(d[-2:]) for d in rule.get("BYDAY", "").split(",") if d[-2:] in DAYS}
    n, day = 0, start
    while day <= min(end, until) and (count is None or n < count):
        weeks = (day.date() - start.date()).days // 7
        on_week = freq == "DAILY" or weeks % step == 0
        on_day = not days or day.weekday() in days if freq == "WEEKLY" else True
        if freq == "DAILY" and (day.date() - start.date()).days % step:
            on_day = False
        if on_week and on_day:
            n += 1
            yield day
        day += dt.timedelta(days=1)


def next_event(text, now):
    local = now.tzinfo
    soonest = None
    for start, summary, rule in events(text, local):
        for when in occurrences(start, rule, now + LOOKAHEAD):
            if when >= now and (soonest is None or when < soonest[0]):
                soonest = (when, summary)
                break
    return soonest


@dataclass(frozen=True)
class State:
    when: str | None  # "HH:MM" (or a weekday) of the next event; None when there is none
    minutes: int = 0
    title: str = ""
    connected: bool = True


class AgendaScreen:
    APP = "agenda"
    TICK = 120.0

    def __init__(self, options=None, settings=None, get=net.get, clock=None):
        self.settings, self.get = settings, get
        self.clock = clock or (lambda: dt.datetime.now().astimezone())

    def sample(self):
        url = connections.value(self.settings, "calendar", "ics_url")
        if not url:
            return State(None, connected=False)
        now = self.clock()
        found = next_event(self.get(url).decode("utf-8", "replace"), now)
        if found is None:
            return State(None)
        when, title = found
        local = when.astimezone(now.tzinfo)
        label = (
            local.strftime("%H:%M") if local.date() == now.date() else local.strftime("%a").upper()
        )
        return State(label, int((when - now).total_seconds() // 60), title)

    def render(self, state):
        if state.when is None:
            c = Canvas()
            c.text(1, 2, "CALENDAR", LED["label"], big=False)
            c.text(
                1, 9, "CONNECT" if not state.connected else "NOTHING NEXT", LED["gray"], big=False
            )
            return Animation.still(c, key=state)
        table = font.for_text(state.title)
        cjk = table not in (font.BIG, font.SMALL)
        lead = f"IN {state.minutes}M" if state.minutes < 60 else f"IN {state.minutes // 60}H"

        def static(c):
            if not cjk:
                c.rect(0, 0, 52, 7, 0)
                c.text(1, 1, state.when, LED["amber"], big=False)
                c.text(25, 1, lead, LED["label"], big=False)

        y = 3 if cjk else 9
        frames = ticker.frames(static, state.title, y, LED["white"], table if cjk else font.SMALL)
        return Animation(frames, ticker.FRAME_MS, key=state)
