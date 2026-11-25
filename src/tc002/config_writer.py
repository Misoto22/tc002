"""Write Settings back to tc002.toml in a canonical, commented layout.

Python's stdlib reads TOML but cannot write it; the file's shape is small and fixed,
so this emitter covers exactly what tc002.toml uses: tables, nested tables, arrays and
inline tables of strings, numbers and booleans.
"""

import hashlib
import json
import os
import tempfile
import threading
from pathlib import Path

from . import builtins
from .config import to_data

HEADER = """\
# tc002 configuration — the single source of every setting tc002 manages.
# Edit by hand or with `tc002 ui`; apply with `tc002 layout apply` (the UI applies for you).
# Machine-local facts (the clock's IP) are kept by `tc002 setup`, never here.
"""

COMMENTS = {
    "screens": "Live screens run by the background service: claude, usage, sys.",
    "device": "Built-in apps that stay on; `tc002 layout apply` turns every other one off.\n"
    + "\n".join(
        f"{cat}: {' '.join(k for k, b in builtins.CATALOGUE.items() if b.category == cat)}"
        for cat in ("tools", "social", "calendar")
    ),
    "display": "Clock-wide settings, applied with /setConfig. Omit a key to leave it as is.",
    "apps": "Settings of built-in apps (no credentials: those stay on the device).",
    "rotation": "Replaces the device's own carousel. Each slot is a screen or a kept built-in.\n"
    'mode = "single" holds `show` (one screen or built-in) instead of stepping through slots.',
    "alerts": "A Claude Code session waiting for you takes over the clock until you answer.",
    "night": "The screen fully dark every night, between two times on this Mac's clock.\n"
    "The background service puts a black screen up at `start` and takes it down at `end`.",
    "screen": "Options of tc002's own screens, one table each (see `tc002 ui` for every\n"
    "option): [screen.countdown] date and label, [screen.worldclock] zones, [screen.focus]\n"
    "minutes and break_minutes, [screen.progress] week_start, [screen.stocks] symbols,\n"
    "[screen.hackernews] list and min_points, [screen.home] entities.",
    "connections": "Plain settings of services API screens use (secrets stay in the Keychain):\n"
    "[connections.homeassistant] url.",
    "appearance": "Colours of tc002's screens on the clock: led_theme is one of match, classic,\n"
    'paper, matcha, ai, sakura, kohaku ("match" follows ui_palette, the UI\'s colour theme).',
}


def _value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int | float):
        return str(int(v)) if float(v).is_integer() else repr(float(v))
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)  # a JSON string is a valid TOML basic string
    if isinstance(v, list):
        return "[" + ", ".join(_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_value(x)}" for k, x in v.items()) + " }"
    raise TypeError(f"cannot write {type(v).__name__} to TOML")


def _table(name, body, lines):
    scalars = {k: v for k, v in body.items() if not isinstance(v, dict) or name == "rotation"}
    nested = {k: v for k, v in body.items() if isinstance(v, dict) and name != "rotation"}
    lines.append(f"[{name}]")
    for key, value in scalars.items():
        if name == "rotation" and key == "slots":
            lines.append("slots = [")
            lines.extend(f"  {_value(slot)}," for slot in value)
            lines.append("]")
        else:
            lines.append(f"{key} = {_value(value)}")
    lines.append("")
    for key, value in nested.items():
        _table(f"{name}.{key}", value, lines)


EXAMPLES = {
    "display": '[display]\nvolume = 2\ntimezone = "UTC+1"\nbrightness = { level = "mid" }',
    "apps": '[apps.clock]\ntimeFormat = "HH:MM"\n\n[apps.weather]\ncity = "Berlin"',
    "night": '[night]\nenable = true\nstart = "23:00"\nend = "07:00"',
    "screen": '[screen.countdown]\ndate = "2027-01-01"\nlabel = "NEW YEAR"',
    "connections": '[connections.homeassistant]\nurl = "http://homeassistant.local:8123"',
}


def dump(settings):
    lines = [HEADER]
    for section, body in to_data(settings).items():
        if not body and section in EXAMPLES:  # show what can go here, commented out
            lines.extend(f"# {line}" for line in COMMENTS[section].splitlines())
            lines.extend(f"# {line}" if line else "#" for line in EXAMPLES[section].splitlines())
            lines.append("")
            continue
        lines.extend(f"# {line}" for line in COMMENTS[section].splitlines())
        _table(section, body, lines)
    return "\n".join(lines).rstrip() + "\n"


# Every writer in this process (web UI requests run in threads) takes this lock around
# its read-modify-write, so two requests cannot each read the old file and the second
# silently undo the first. Re-entrant: a quick setting saves through save_config.
WRITE_LOCK = threading.RLock()


def version(path):
    """A fingerprint of the file as it is on disk; None when it does not exist. The UI
    sends back the one it loaded, so a save cannot overwrite a file changed meanwhile."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
    except FileNotFoundError:
        return None


def save(settings, path):
    """Atomically replace `path` so a crash never leaves a half-written config."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tc002-", suffix=".toml")
    with os.fdopen(fd, "w") as f:
        f.write(dump(settings))
    os.replace(tmp, path)
