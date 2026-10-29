"""Token usage of coding agents (Claude Code, Codex), read from their local files.

Nothing here touches the network or an account: each agent already writes its token
counts to disk, and these readers only add them up for "today" and "the last 5 hours".
"""

import time
from dataclasses import dataclass

FIVE_HOURS = 5 * 3600


@dataclass(frozen=True)
class Usage:
    today: int  # tokens since local midnight
    window: int  # tokens in the last five hours
    limit_5h: float | None = None  # % of the 5-hour allowance used, when the agent reports it
    limit_week: float | None = None  # % of the weekly allowance used
    source: str = "none"  # which file the numbers came from; "none" when the agent is absent


def day_start(now=None):
    """Local midnight before `now`, as a Unix time."""
    t = time.localtime(now if now is not None else time.time())
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


def short(n):
    """12 -> "12", 8420 -> "8.4K", 1234567 -> "1.2M"; fits the clock's small screen."""
    for size, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= size:
            value = n / size
            return f"{value:.1f}{suffix}" if value < 10 else f"{value:.0f}{suffix}"
    return str(int(n))


def rough(n):
    """Two significant figures, so a screen keyed on usage re-renders only on real change."""
    if n < 100:
        return int(n)
    digits = len(str(int(n))) - 2
    return int(round(n, -digits))
