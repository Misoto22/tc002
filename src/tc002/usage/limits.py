"""Claude Code's plan limits (5-hour and 7-day, % used), saved where every reader finds them.

Two writers keep this file current:
  - `tc002 statusline`: Claude Code pipes a JSON document to the status line after each
    reply; on a subscription it carries `rate_limits.five_hour` / `seven_day` with
    `used_percentage` and `resets_at`.
  - claude_login.py: asks Anthropic's usage endpoint with Claude Code's own login, for
    sessions that never run a status line (the desktop app).
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

PATH = Path(os.environ.get("TC002_LIMITS_FILE", "~/.cache/tc002/claude-limits.json")).expanduser()
WINDOWS = {"five_hour": "limit_5h", "seven_day": "limit_week"}


def _epoch(value):
    """resets_at as a Unix time, whether it arrives as seconds or as an ISO timestamp."""
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _percent(value):
    return round(float(value), 1) if isinstance(value, int | float) else None


def record(status_input, path=None, now=None):
    """Save the rate limits from one status line input; returns False when it has none."""
    return _save((status_input or {}).get("rate_limits"), "used_percentage", path, now)


def record_usage_reply(reply, path=None, now=None):
    """Save the limits from Anthropic's /api/oauth/usage reply (`utilization` per window)."""
    return _save(reply, "utilization", path, now)


def age(path=None, now=None):
    """Seconds since the limits were last saved; infinity when they never were."""
    try:
        at = float(json.loads((path or PATH).read_text())["at"])
    except OSError, ValueError, KeyError, TypeError:
        return float("inf")
    return (time.time() if now is None else now) - at


def _save(limits, field, path, now):
    if not isinstance(limits, dict):
        return False
    saved = {}
    for window in WINDOWS:
        part = limits.get(window) or {}
        pct = _percent(part.get(field))
        if pct is not None:
            saved[window] = {"used": pct, "resets_at": _epoch(part.get("resets_at"))}
    if not saved:
        return False
    path = path or PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"at": time.time() if now is None else now, **saved}))
    tmp.replace(path)
    return True


def latest(path=None, now=None):
    """{"limit_5h": %, "reset_5h": t, "limit_week": %, "reset_week": t}; {} when unknown.

    A window whose reset time has passed since it was saved reads as 0 %: the
    allowance refilled, and the status line has not run since to say so.
    """
    try:
        data = json.loads((path or PATH).read_text())
    except OSError, ValueError:
        return {}
    now = time.time() if now is None else now
    out = {}
    for window, name in WINDOWS.items():
        part = data.get(window)
        if not isinstance(part, dict) or _percent(part.get("used")) is None:
            continue
        resets = part.get("resets_at")
        expired = isinstance(resets, int | float) and resets <= now
        out[name] = 0.0 if expired else _percent(part["used"])
        out["reset" + name.removeprefix("limit")] = None if expired else resets
    return out
