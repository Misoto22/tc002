"""Claude Code sessions as tc002 sees them: working, waiting for you, done or idle.

`tc002 hook` is the command every Claude Code hook runs. It reads the hook's JSON from
stdin and writes one small file per session under ~/.cache/tc002/sessions/, so sessions
that fire hooks at the same moment never race on a shared file. Hooks must return at
once and never touch the network, so they only record; screens and the UI read here.

Some states are settled at read time rather than by a hook:
  waiting -> working  when the transcript grows after the wait began (you answered)
  working -> idle     when the transcript has been quiet for STALE seconds
  done    -> idle     once DONE_UNREAD seconds have passed without a new prompt
"""

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .. import paths

DIR = Path(os.environ.get("TC002_SESSIONS_DIR", paths.CACHE_DIR / "sessions"))
STATES = ("working", "waiting", "done", "idle")
# hook event -> state it sets; SessionEnd forgets the session
HOOKS = {
    "SessionStart": "idle",
    "UserPromptSubmit": "working",
    "Notification": "waiting",
    "Stop": "done",
    "SessionEnd": None,
}
ANSWERED_GRACE = 2.0  # transcript writes this soon after a wait are the wait itself
STALE = 6 * 3600
DONE_UNREAD = 3600
FORGET = 24 * 3600
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
# Claude Code also notifies after 60 s of idleness; that is not a question for you.
_IDLE_NOTICE = ("waiting for your input", "idle_prompt")


@dataclass(frozen=True)
class Session:
    id: str
    project: str  # folder name the session runs in
    state: str
    since: float  # when the session entered this state
    message: str = ""  # what it is waiting for, when it is waiting
    transcript: str = ""


def _path(session_id, root):
    if not isinstance(session_id, str) or not _SAFE_ID.match(session_id):
        raise ValueError("hook input has no usable session_id")
    return (root or DIR) / f"{session_id}.json"


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.replace(path)


def _read(path):
    try:
        return json.loads(path.read_text())
    except OSError, ValueError:
        return None


def record_hook(payload, root=None, now=None):
    """Apply one hook's stdin JSON; returns the state written (None when forgotten)."""
    event = payload.get("hook_event_name")
    if event not in HOOKS:
        raise ValueError(f"unsupported hook event {event!r}")
    path = _path(payload.get("session_id"), root)
    if event == "SessionEnd":
        path.unlink(missing_ok=True)
        return None
    previous = _read(path) or {}
    state = HOOKS[event]
    message = str(payload.get("message") or "")
    if event == "Notification" and _is_idle_notice(payload, message):
        state = previous.get("state", "idle")
    if event == "SessionStart" and previous.get("state") in ("working", "waiting"):
        state = previous["state"]  # a resume does not end a running turn
    cwd = str(payload.get("cwd") or previous.get("cwd") or "")
    _write(
        path,
        {
            "state": state,
            "since": previous.get("since") if state == previous.get("state") else _now(now),
            "cwd": cwd,
            "message": message[:200] if state == "waiting" else "",
            "transcript": str(payload.get("transcript_path") or previous.get("transcript", "")),
        },
    )
    return state


# `tc002 event <kind>` (older hooks, scripts): one shared pseudo-session
MANUAL = {"done": "Stop", "wait": "Notification", "clear": "UserPromptSubmit"}


def record_manual(kind, root=None, now=None):
    if kind not in MANUAL:
        raise ValueError(f"unknown event {kind!r}; expected one of {tuple(MANUAL)}")
    payload = {"hook_event_name": MANUAL[kind], "session_id": "manual", "cwd": "manual"}
    return record_hook(payload, root, now)


def _is_idle_notice(payload, message):
    kind = str(payload.get("notification_type") or "")
    return kind in _IDLE_NOTICE or any(n in message.lower() for n in _IDLE_NOTICE)


def _now(now):
    return time.time() if now is None else now


def _mtime(path):
    try:
        return os.path.getmtime(path) if path else 0.0
    except OSError:
        return 0.0


def _settle(state, since, written, now):
    """The state a recorded one has become by `now` (see the module docstring)."""
    if state == "waiting" and written > since + ANSWERED_GRACE:
        return "working", written
    if state == "working" and written and now - written > STALE:
        return "idle", written
    if state == "done" and now - since > DONE_UNREAD:
        return "idle", since
    return state, since


def load(root=None, now=None):
    """Every known session, newest change first; forgets ones untouched for FORGET seconds."""
    now, root = _now(now), root or DIR
    sessions = []
    for path in root.glob("*.json") if root.is_dir() else ():
        data = _read(path)
        if not data or data.get("state") not in STATES:
            continue
        written = _mtime(data.get("transcript"))
        since = float(data.get("since") or 0)
        if now - max(since, written) > FORGET:
            path.unlink(missing_ok=True)
            continue
        state, since = _settle(data["state"], since, written, now)
        cwd = data.get("cwd", "")
        sessions.append(
            Session(
                path.stem,
                os.path.basename(cwd.rstrip("/")) or "session",
                state,
                since,
                data.get("message", "") if state == "waiting" else "",
                data.get("transcript", ""),
            )
        )
    return sorted(sessions, key=lambda s: -s.since)


def counts(sessions):
    """{state: number of sessions} for every state, zeros included."""
    tally = dict.fromkeys(STATES, 0)
    for s in sessions:
        tally[s.state] += 1
    return tally
