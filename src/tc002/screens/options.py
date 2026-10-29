"""Options of tc002's own screens: what `[screen.<name>]` in tc002.toml may set.

A screen declares OPTIONS = {key: (kind, default, spec)}; the same table validates
tc002.toml, fills in defaults, and describes the UI's controls, so an option is defined
once, next to the screen that uses it.

Kinds: "text" (spec: max length), "date" (YYYY-MM-DD), "zones" (IANA time zones; spec:
how many), "list" (short texts; spec: how many), "int" (spec: (min, max)), "choice"
(spec: allowed values), "symbols" (market symbols as Yahoo Finance writes them, picked
by search in the UI; spec: how many), "entities" (Home Assistant entity ids, picked from
the user's Home Assistant; spec: how many).
"""

import datetime as dt
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SYMBOL = re.compile(r"^[A-Z0-9^][A-Z0-9^.=\-]{0,14}$")  # AAPL, ^GSPC, 0700.HK, BTC-USD
ENTITY = re.compile(r"^[a-z_]+\.[a-z0-9_]+$")  # sensor.living_room_temperature
PATTERNS = {"symbols": SYMBOL, "entities": ENTITY}


def rules(screen_class):
    return getattr(screen_class, "OPTIONS", {})


def _check(where, rule, value):
    kind, _, spec = rule
    if kind == "text" and not (isinstance(value, str) and len(value) <= spec):
        return f"{where} must be text of at most {spec} characters"
    if kind == "int":
        lo, hi = spec
        if not isinstance(value, int) or isinstance(value, bool) or not lo <= value <= hi:
            return f"{where} must be a whole number from {lo} to {hi}"
    if kind == "choice" and value not in spec:
        return f"{where} must be one of {list(spec)}"
    if kind == "date":
        try:
            dt.date.fromisoformat(value)
        except TypeError, ValueError:
            return f"{where} must be a date like 2027-01-01"
    if kind == "list" and not (
        isinstance(value, list)
        and 1 <= len(value) <= spec
        and all(isinstance(v, str) and 0 < len(v) <= 64 for v in value)
    ):
        return f"{where} must list 1 to {spec} names"
    if kind in PATTERNS and not (
        isinstance(value, list)
        and 1 <= len(value) <= spec
        and all(isinstance(v, str) and PATTERNS[kind].match(v) for v in value)
    ):
        what = "symbols like AAPL or 0700.HK" if kind == "symbols" else "entity ids"
        return f"{where} must list 1 to {spec} {what}"
    if kind == "zones":
        if not isinstance(value, list) or not 1 <= len(value) <= spec:
            return f"{where} must list 1 to {spec} time zones"
        for zone in value:
            try:
                ZoneInfo(zone)
            except ZoneInfoNotFoundError, ValueError, TypeError:
                return f"{where}: unknown time zone {zone!r} (use a name like Europe/London)"
    return None


def validate(screens, options):
    """Problems with the [screen.*] tables, given SCREENS (empty list when valid)."""
    problems = []
    for name, values in options.items():
        if name not in screens:
            problems.append(f"screen.{name}: no such screen")
            continue
        table = rules(screens[name])
        for key, value in values.items():
            if key not in table:
                problems.append(f"screen.{name}.{key} is not an option of this screen")
            elif msg := _check(f"screen.{name}.{key}", table[key], value):
                problems.append(msg)
    return problems


def resolved(screen_class, values):
    """Every option with its default filled in."""
    return {key: values.get(key, default) for key, (_, default, _) in rules(screen_class).items()}


def describe(screens):
    """For the UI: {screen: {option: {kind, default, spec}}} for screens that have options."""
    return {
        name: {k: {"kind": kind, "default": d, "spec": s} for k, (kind, d, s) in rules(cls).items()}
        for name, cls in screens.items()
        if rules(cls)
    }
