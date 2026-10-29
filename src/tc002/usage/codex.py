"""Codex token usage and allowance from its home directory ($CODEX_HOME, else ~/.codex).

Preferred source: rollout logs (sessions/**/rollout-*.jsonl, archived_sessions/*.jsonl),
whose `token_count` events carry per-turn tokens and the 5-hour / weekly allowance used.
Fallback: the newest state_*.sqlite, whose `threads.tokens_used` holds a running total per
conversation (attributed to the time the conversation was last updated). Both are read
only; the database is opened read-only.
"""

import glob
import json
import os
import sqlite3
import time
from datetime import datetime

from . import FIVE_HOURS, Usage, day_start


def home():
    return os.path.expanduser(os.environ.get("CODEX_HOME", "~/.codex"))


def _rollouts(root, since):
    patterns = ("sessions/**/rollout-*.jsonl", "archived_sessions/rollout-*.jsonl")
    paths = (
        p for pattern in patterns for p in glob.glob(os.path.join(root, pattern), recursive=True)
    )
    return [p for p in paths if os.path.getmtime(p) >= since]


def _events(path):
    """(unix time, tokens this turn, rate_limits or None) for each token_count event."""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"token_count"' not in line:
                continue
            try:
                record = json.loads(line)
                payload = record.get("payload") or {}
                if payload.get("type") != "token_count":
                    continue
                at = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")).timestamp()
                last = ((payload.get("info") or {}).get("last_token_usage") or {}).get(
                    "total_tokens", 0
                )
                yield at, int(last or 0), payload.get("rate_limits")
            except ValueError, KeyError, TypeError, AttributeError:
                continue


def _percent(limit):
    value = (limit or {}).get("used_percent")
    return round(float(value), 1) if isinstance(value, int | float) else None


def from_rollouts(root, now):
    since = min(day_start(now), now - FIVE_HOURS)
    paths = _rollouts(root, since)
    if not paths:
        return None
    today = window = 0
    latest = (0, None)
    for path in paths:
        for at, tokens, limits in _events(path):
            if at >= day_start(now):
                today += tokens
            if at >= now - FIVE_HOURS:
                window += tokens
            if limits and at > latest[0]:
                latest = (at, limits)
    limits = latest[1] or {}
    return Usage(
        today,
        window,
        _percent(limits.get("primary")),
        _percent(limits.get("secondary")),
        source="codex-rollouts",
    )


def from_database(root, now):
    databases = sorted(glob.glob(os.path.join(root, "state_*.sqlite")))
    if not databases:
        return None
    try:
        with sqlite3.connect(f"file:{databases[-1]}?mode=ro", uri=True, timeout=1) as db:
            rows = db.execute(
                "SELECT tokens_used, updated_at FROM threads WHERE updated_at >= ?",
                (int(min(day_start(now), now - FIVE_HOURS)),),
            ).fetchall()
    except sqlite3.Error:
        return None  # schema changed or database locked: report nothing rather than guess
    today = sum(t for t, at in rows if at >= day_start(now))
    window = sum(t for t, at in rows if at >= now - FIVE_HOURS)
    return Usage(today, window, source="codex-database")


class CodexUsage:
    def __init__(self, root=None, clock=time.time):
        self.root, self.clock = root, clock

    def collect(self):
        root, now = self.root or home(), self.clock()
        if not os.path.isdir(root):
            return Usage(0, 0)
        return from_rollouts(root, now) or from_database(root, now) or Usage(0, 0)
