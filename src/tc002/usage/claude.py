"""Claude Code token usage from its session transcripts (~/.claude/projects/**/*.jsonl).

Every assistant message carries `message.usage`; streamed replies are written more than
once, so entries are de-duplicated by (message id, request id), the same rule ccusage
uses. Files are read incrementally: only bytes appended since the last call are parsed.
"""

import glob
import json
import os
import time
from datetime import datetime

from . import FIVE_HOURS, Usage, day_start, limits

PROJECTS = os.path.expanduser("~/.claude/projects")
KEEP = 26 * 3600  # entries older than this can never count again


def _tokens(usage):
    return sum(
        int(usage.get(k) or 0)
        for k in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        )
    )


def _entry(line):
    """(unix time, dedupe key, tokens) for one transcript line, or None."""
    if '"usage"' not in line:
        return None
    try:
        record = json.loads(line)
        message = record.get("message") or {}
        usage = message.get("usage")
        if record.get("type") != "assistant" or not usage:
            return None
        at = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")).timestamp()
    except ValueError, KeyError, TypeError, AttributeError:
        return None  # a malformed or half-written line is skipped, not fatal
    key = (message.get("id"), record.get("requestId")) if message.get("id") else None
    return at, key, _tokens(usage)


class ClaudeUsage:
    def __init__(self, projects=PROJECTS, clock=time.time):
        self.projects, self.clock = projects, clock
        self._files = {}  # path -> (bytes read, [entries])

    def _read(self, path):
        offset, entries = self._files.get(path, (0, []))
        try:
            size = os.path.getsize(path)
            if size < offset:  # rewritten: start over
                offset, entries = 0, []
            if size == offset:
                return entries
            with open(path, "rb") as f:
                f.seek(offset)
                chunk = f.read()
        except OSError:
            return entries
        end = chunk.rfind(b"\n") + 1  # leave a half-written last line for next time
        for raw in chunk[:end].decode("utf-8", "replace").splitlines():
            if (entry := _entry(raw)) is not None:
                entries.append(entry)
        self._files[path] = (offset + end, entries)
        return entries

    def collect(self):
        now = self.clock()
        since = min(day_start(now), now - FIVE_HOURS)
        files = [
            p
            for p in glob.glob(os.path.join(self.projects, "**", "*.jsonl"), recursive=True)
            if os.path.getmtime(p) >= since
        ]
        for path in list(self._files):
            if path not in files:
                del self._files[path]
        seen, today, window = set(), 0, 0
        midnight = day_start(now)
        for path in files:
            entries = [e for e in self._read(path) if e[0] >= now - KEEP]
            self._files[path] = (self._files.get(path, (0, []))[0], entries)
            for at, key, tokens in entries:
                if key is not None:
                    if key in seen:
                        continue
                    seen.add(key)
                if at >= midnight:
                    today += tokens
                if at >= now - FIVE_HOURS:
                    window += tokens
        return Usage(
            today,
            window,
            source="claude-transcripts" if files else "none",
            **limits.latest(now=now),
        )
