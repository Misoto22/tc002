"""Claude Code sessions: how many are running, asking for you, and finished.

Layout (52x16), three columns split by dim 1 px rules at x 17 and x 35:
  RUN (sky)  ASK (amber)  OK (green) -- a 5x7 count over a 3x5 label; a zero column
  is grey. ASK blinks while anything waits; a dot runs under RUN while work is going on.
A session that starts waiting takes the whole screen (bell, project, NEEDS YOU) until
you answer; one that finishes shows DONE and its project for a few seconds.

States come from the hooks (runtime/sessions.py). Without hooks, transcripts written
in the last SESSION_WINDOW seconds still count as running.
"""

import glob
import os
import time
from dataclasses import dataclass

from ..render import font
from ..render.anim import Animation
from ..render.canvas import Canvas
from ..render.palette import LED
from ..runtime import sessions

PROJECTS = os.path.expanduser("~/.claude/projects")
SESSION_WINDOW = 180
DONE_SECONDS = 5
COLUMNS = (  # x, width, label, colour, state counted
    (0, 17, "RUN", LED["sky"], "working"),
    (18, 17, "ASK", LED["amber"], "waiting"),
    (36, 16, "OK", LED["green"], "done"),
)
BELL = ["..#..", ".###.", ".###.", ".###.", "#####", ".....", "..#.."]
CHECK = [".......", "......#", ".....#.", "#...#..", ".#.#...", "..#....", "......."]
NAME_X = 11


@dataclass(frozen=True)
class State:
    working: int
    waiting: int
    done: int
    alert: tuple[str, str] | None = None  # ("wait" | "done", project)


def unhooked_transcripts(projects, now, known):
    """Transcripts written recently by sessions the hooks have not told us about."""
    count = 0
    for path in glob.glob(os.path.join(projects, "*", "*.jsonl")):
        if path not in known and now - os.path.getmtime(path) <= SESSION_WINDOW:
            count += 1
    return count


class ClaudeScreen:
    """Samples session states; renders a GIF that only changes with them."""

    APP = "claude"
    TICK = 2.0

    def __init__(self, projects=PROJECTS, clock=time.time, root=None):
        self.projects, self.clock, self.root = projects, clock, root

    def sample(self):
        now = self.clock()
        known = sessions.load(self.root, now)
        tally = sessions.counts(known)
        extra = unhooked_transcripts(self.projects, now, {s.transcript for s in known})
        return State(tally["working"] + extra, tally["waiting"], tally["done"], _alert(known, now))

    def render(self, state):
        if state.alert:
            kind, project = state.alert
            return Animation(*_alert_frames(kind, project), key=state)
        return Animation(*_overview_frames(state), key=state)


def _alert(known, now):
    waiting = [s for s in known if s.state == "waiting"]
    if waiting:
        return "wait", min(waiting, key=lambda s: s.since).project  # longest wait first
    fresh = [s for s in known if s.state == "done" and now - s.since < DONE_SECONDS]
    return ("done", fresh[0].project) if fresh else None


def _centred(c, x0, width, y, text, colour, big):
    table = font.BIG if big else font.SMALL
    c.text(x0 + (width - font.text_width(table, text)) // 2, y, text, colour, big)


def _overview(state, f):
    c = Canvas()
    counts = {"working": state.working, "waiting": state.waiting, "done": state.done}
    for x0, width, label, colour, key in COLUMNS:
        n = counts[key]
        lit = n > 0 and not (key == "waiting" and (f // 5) % 2)
        _centred(c, x0, width, 1, str(min(n, 9)), colour if lit else LED["gray"], True)
        _centred(c, x0, width, 10, label, LED["label"] if n else LED["dim"], False)
    for x in (17, 35):
        c.rect(x, 2, 1, 12, LED["dim"])
    if state.working:
        c.set(1 + f % 15, 15, LED["sky"])
    return c


def _overview_frames(state):
    if state.working or state.waiting:
        frames = [_overview(state, f) for f in range(30)]
        return frames, [100] * len(frames)
    return [_overview(state, 0)], [5000]


def _name(c, project, y_big, y_small, colour):
    text = project.upper()
    if font.text_width(font.BIG, text) <= 52 - NAME_X:
        c.text(NAME_X, y_big, text, colour, True)
    else:
        c.text(NAME_X, y_small, text[:10], colour, False)


def _alert_frames(kind, project):
    frames = []
    if kind == "wait":
        for dx in (0, -1, 0, 1):  # the bell swings
            c = Canvas()
            c.sprite(3 + dx, 2, BELL, LED["amber"])
            _name(c, project, 1, 2, LED["white"])
            c.text(NAME_X, 10, "NEEDS YOU", LED["amber"], False)
            frames.append(c)
        return frames * 3, [150] * 12
    c = Canvas()
    c.sprite(1, 2, CHECK, LED["green"])
    c.text(NAME_X, 1, "DONE", LED["white"], True)
    c.text(NAME_X, 10, project.upper()[:10], LED["green"], False)
    return [c], [DONE_SECONDS * 1000]
