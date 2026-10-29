"""Rules for the clock's own settings that tc002.toml may set: `[display]` and `[apps.*]`.

One table per setting, taken from the protocol reference (sections 5.1 and 5.6). The
same tables validate tc002.toml and drive the web UI's controls (`schema()`), so an
allowed value is defined exactly once. Credentials (OAuth tokens, calendar passwords,
the weather API key) are deliberately not settable here: they stay on the device. The
one way to give the clock a social token is write-only (`TOKEN_APPS`, web/api.py): sent
to the clock, never stored, never read back.
"""

from . import builtins

TIMEZONES = [f"UTC{n:+d}" if n else "UTC+0" for n in range(-12, 13)]

# key: (kind, label, options or (min, max))
DISPLAY = {
    "volume": ("int", "Volume", (0, 6)),
    "timezone": ("choice", "Time zone", TIMEZONES),
    "dateFormat": ("choice", "Date format", ["MM/DD", "DD/MM"]),
    "showWeek": ("bool", "Show weekday on clock", None),
    "weekStart": ("choice", "Week starts on", [1, 0]),  # 1 = Monday, 0 = Sunday
    "scrollSpeed": ("int", "Text scroll speed", (0, 10)),
    "lowBatteryAutoSleep": ("bool", "Sleep on low battery", None),
}
BRIGHTNESS_LEVELS = ["low", "mid", "high"]
BRIGHTNESS_RANGE = (5, 100)  # % the firmware accepts per level
BRIGHTNESS_DEFAULTS = {"level": "high", "low": 50, "mid": 80, "high": 100}

APPS = {
    "clock": {"timeFormat": ("choice", "Time format", ["HH:MM", "HH:MM:SS", "HH:MM AP"])},
    "weather": {
        "city": ("text", "City", None),
        "lat": ("text", "Latitude", None),
        "lon": ("text", "Longitude", None),
        "displayInfo": (
            "flags",
            "Show",
            ["displayTemperature", "displayHumidity", "displayPressure", "displayAqi"],
        ),
    },
    "busy": {
        "focusTime": ("choice", "Focus minutes", ["30", "45", "60"]),
        "relaxTime": ("choice", "Break minutes", ["5", "10", "15"]),
    },
    "tomato": {
        "focusTime": ("choice", "Focus minutes", ["10", "15", "25"]),
        "relaxTime": ("choice", "Break minutes", ["5", "10", "15"]),
    },
    # every social counter: whose account it shows (protocol 5.4, `uid`)
    **{
        key: {"uid": ("text", "Account ID", None)}
        for key, app in builtins.CATALOGUE.items()
        if app.category == "social"
    },
}
# Social apps the clock also needs an OAuth token for (protocol 5.4).
TOKEN_APPS = ("weibo", "youtube", "instagram")


def _check(where, rule, value):
    kind, _, spec = rule
    if kind == "bool" and not isinstance(value, bool):
        return f"{where} must be true or false"
    if kind == "int":
        lo, hi = spec
        if not isinstance(value, int) or isinstance(value, bool) or not lo <= value <= hi:
            return f"{where} must be an integer {lo}-{hi}"
    if kind == "choice" and value not in spec:
        return f"{where} must be one of {spec}"
    if kind == "text" and not isinstance(value, str):
        return f"{where} must be text"
    if kind == "flags":
        if not isinstance(value, dict) or set(value) - set(spec):
            return f"{where} keys must be among {spec}"
        if not any(value.values()):
            return f"{where} needs at least one item set to true"
    return None


def validate_display(display):
    """List of problems with a `[display]` table (empty when valid)."""
    problems = []
    for key, value in display.items():
        if key == "brightness":
            problems += _validate_brightness(value)
        elif key in DISPLAY:
            if msg := _check(f"display.{key}", DISPLAY[key], value):
                problems.append(msg)
        else:
            problems.append(f"display.{key} is not a known setting")
    return problems


def _validate_brightness(value):
    if not isinstance(value, dict):
        return ["display.brightness must be a table"]
    problems = []
    if "level" in value and value["level"] not in BRIGHTNESS_LEVELS:
        problems.append(f"display.brightness.level must be one of {BRIGHTNESS_LEVELS}")
    percents = [value.get(k) for k in BRIGHTNESS_LEVELS]
    if any(p is not None for p in percents):
        lo, hi = BRIGHTNESS_RANGE
        if not all(isinstance(p, int) and lo <= p <= hi for p in percents):
            problems.append(f"display.brightness low/mid/high must all be set, {lo}-{hi}")
        elif not percents[0] < percents[1] < percents[2]:
            problems.append("display.brightness must rise: low < mid < high")
    if extra := set(value) - {"level", *BRIGHTNESS_LEVELS}:
        problems.append(f"display.brightness has unknown keys {sorted(extra)}")
    return problems


def validate_apps(apps):
    """List of problems with the `[apps.*]` tables (empty when valid)."""
    problems = []
    for app, fields in apps.items():
        rules = APPS.get(app)
        if rules is None:
            problems.append(f"apps.{app}: settings exist only for {sorted(APPS)}")
            continue
        for key, value in fields.items():
            if key not in rules:
                problems.append(f"apps.{app}.{key} is not a known setting")
            elif msg := _check(f"apps.{app}.{key}", rules[key], value):
                problems.append(msg)
    return problems


def schema():
    """Controls description for the web UI."""

    def describe(rules):
        return {
            key: {"kind": kind, "label": label, "options": spec}
            for key, (kind, label, spec) in rules.items()
        }

    return {
        "display": describe(DISPLAY),
        "brightnessLevels": BRIGHTNESS_LEVELS,
        "brightnessRange": list(BRIGHTNESS_RANGE),
        "brightnessDefaults": BRIGHTNESS_DEFAULTS,
        "apps": {app: describe(rules) for app, rules in APPS.items()},
        "tokenApps": list(TOKEN_APPS),
    }
