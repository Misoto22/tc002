"""Night: the clock's screen fully dark, on a schedule or right now.

How it goes dark: a custom app named `night` whose only frame is black is pushed and
switched to. Every LED is then off, and since tc002 turns the clock's own carousel off,
nothing switches away from it on its own: the screen stays dark even if the Mac sleeps.
While it is dark the background service switches and pushes nothing (`Watch`), because
any switch lights the screen again.

Why not the firmware's own `nightMode` (an undocumented /setConfig field)? Measured on
firmware 2.0.4 it darkened the screen once and then ignored every later window, wrapping
or not, built-in app or custom; it cannot be relied on.

Two ways in:

- `[night]` in tc002.toml: `enable`, `start`, `end` ("HH:MM" on this Mac's clock, so no
  time zone sums). The service follows it.
- "Screen off now" / "screen on now" (`turn_off`, `turn_on`): a small state file that
  overrides the schedule until its `until` (or, for "off", until turned back on).
"""

import contextlib
import json
import os
import threading
import time
from pathlib import Path

from . import paths
from .device import DeviceError
from .render.anim import Animation
from .render.canvas import Canvas

PATH = Path(os.environ.get("TC002_NIGHT_FILE", paths.CACHE_DIR / "night.json"))
APP = "night"  # the black custom app
DEFAULT = {"enable": False, "start": "23:00", "end": "07:00"}
DAY = 24 * 60
REASSERT = 120  # while dark, switch to the black app again this often (a rebooted clock)


# -- time ---------------------------------------------------------------------------


def parse_hhmm(text):
    """Minutes after midnight for "HH:MM"; ValueError otherwise."""
    if not isinstance(text, str) or len(text) != 5 or text[2] != ":":
        raise ValueError(f"{text!r} is not HH:MM")
    hours, minutes = int(text[:2]), int(text[3:])
    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError(f"{text!r} is not a time of day")
    return hours * 60 + minutes


def hhmm(minutes):
    minutes %= DAY
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def minute_of_day(now=None):
    local = time.localtime(time.time() if now is None else now)
    return local.tm_hour * 60 + local.tm_min


def in_window(schedule, minute):
    """Whether `minute` falls inside an enabled schedule (which may wrap past midnight)."""
    if not schedule.get("enable"):
        return False
    start, end = parse_hhmm(schedule["start"]), parse_hhmm(schedule["end"])
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end


def next_time(target, now=None):
    """Epoch time when this Mac's clock next reads `target` ("HH:MM")."""
    now = time.time() if now is None else now
    gap = (parse_hhmm(target) - minute_of_day(now)) % DAY or DAY
    return now - now % 60 + gap * 60  # on the minute


def schedule_of(settings):
    return {**DEFAULT, **(settings.night if settings else {})}


def validate(night):
    """Problems with a [night] table (empty when valid)."""
    problems = []
    if "enable" in night and not isinstance(night["enable"], bool):
        problems.append("night.enable must be true or false")
    for key in ("start", "end"):
        if key in night:
            try:
                parse_hhmm(night[key])
            except ValueError:
                problems.append(f'night.{key} must be a time like "23:00"')
    merged = {**DEFAULT, **night}
    if merged["start"] == merged["end"]:
        problems.append("night.start and night.end must differ")
    return problems


# -- the override file --------------------------------------------------------------


def override(path=None, now=None):
    """The live override, {"mode": "off" | "on", "until": epoch | None}, or None."""
    try:
        doc = json.loads((path or PATH).read_text())
    except OSError, ValueError:
        return None
    if not isinstance(doc, dict) or doc.get("mode") not in ("off", "on"):
        return None
    now = time.time() if now is None else now
    if doc.get("until") is not None and now >= doc["until"]:
        return None
    return doc


def _write(doc, path=None):
    path = path or PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc))
    tmp.replace(path)


def _clear(path=None):
    (path or PATH).unlink(missing_ok=True)


def dark_now(settings, now=None, path=None):
    """(dark?, why): why is "off", "on" (an override) or "schedule" / None."""
    doc = override(path, now)
    if doc:
        return doc["mode"] == "off", doc["mode"]
    scheduled = in_window(schedule_of(settings), minute_of_day(now))
    return scheduled, ("schedule" if scheduled else None)


# -- the clock ----------------------------------------------------------------------


def black():
    return Animation([Canvas()], [60_000]).payload()


def darken(device):
    """Put the black screen up. Raises DeviceError if the clock does not answer."""
    device.push(APP, black())
    device.switch_custom(APP)


def lighten(device):
    """Take the black screen down; the service shows the rotation again."""
    with contextlib.suppress(DeviceError):
        device.remove(APP)


def turn_off(device, settings=None, until=None, now=None, path=None):
    """Dark now, until the epoch time `until` (None: until turned back on)."""
    darken(device)
    _write({"mode": "off", "since": time.time() if now is None else now, "until": until}, path)
    return status(settings, now, path)


def turn_on(device, settings=None, now=None, path=None):
    """Light now. Inside the night schedule, it stays lit until the schedule ends."""
    now = time.time() if now is None else now
    schedule = schedule_of(settings)
    if in_window(schedule, minute_of_day(now)):
        _write({"mode": "on", "since": now, "until": next_time(schedule["end"], now)}, path)
    else:
        _clear(path)
    if device is not None:
        lighten(device)
    return status(settings, now, path)


def until_morning(settings, now=None):
    """When "off until morning" ends: the schedule's next end, else 07:00."""
    return next_time(schedule_of(settings)["end"] or DEFAULT["end"], now)


def status(settings, now=None, path=None):
    """Everything the UI and `tc002 display status` show."""
    now = time.time() if now is None else now
    dark, why = dark_now(settings, now, path)
    doc = override(path, now)
    schedule = schedule_of(settings)
    nxt = None
    if schedule["enable"] and not doc:
        nxt = next_time(schedule["end" if dark else "start"], now)
    return {
        "dark": dark,
        "why": why,  # "off" / "on" (overrides), "schedule", or None
        "until": doc.get("until") if doc else nxt,
        "schedule": schedule,
        "time": hhmm(minute_of_day(now)),
    }


# -- the background service ---------------------------------------------------------


class Watch:
    """Answers "is the screen meant to be dark now?" for the rotation and screen threads,
    and puts the black screen up (and takes it down) when the answer changes."""

    def __init__(self, device, settings, log=print, clock=time.time, path=None):
        self.device, self.settings, self.log = device, settings, log
        self.clock, self.path = clock, path
        self._lock = threading.Lock()
        self._cache = (None, False)
        self._dark = None  # what the clock was last made to show (None: not yet decided)
        self._shown_at = None  # when the black screen was last (re)asserted

    def dark(self):
        now = self.clock()
        with self._lock:
            at, value = self._cache
            if at is not None and now - at < 1:
                return value
            value, why = dark_now(self.settings, now, self.path)
            if value and (self._shown_at is None or now - self._shown_at >= REASSERT):
                try:
                    darken(self.device)
                    self._shown_at = now
                except DeviceError:
                    self._shown_at = None  # try again next time
            if value != self._dark:
                if value:
                    reason = "screen off" if why == "off" else "night schedule"
                    self.log(f"night: {reason}, black screen up, pausing")
                else:
                    lighten(self.device)  # also clears one left over from a previous run
                    self._shown_at = None
                    if self._dark is not None:
                        self.log("night: over, resuming")
                self._dark = value
            self._cache = (now, value)
            return value
