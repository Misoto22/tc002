"""What the UI shows about coding agents: each session's state and each agent's limits."""

import time
from dataclasses import asdict

from ..runtime import sessions
from ..usage.claude import ClaudeUsage
from ..usage.codex import CodexUsage


class Agents:
    """Keeps the usage readers between requests: they read transcripts incrementally."""

    def __init__(self, clock=time.time):
        self.clock = clock
        self.readers = {"claude": ClaudeUsage(clock=clock), "codex": CodexUsage(clock=clock)}

    def snapshot(self):
        now = self.clock()
        known = sessions.load(now=now)
        return {
            "sessions": [
                {
                    "id": s.id,
                    "project": s.project,
                    "state": s.state,
                    "secondsInState": round(now - s.since),
                    "message": s.message,
                }
                for s in known
            ],
            "counts": sessions.counts(known),
            "usage": {name: asdict(r.collect()) for name, r in self.readers.items()},
        }
