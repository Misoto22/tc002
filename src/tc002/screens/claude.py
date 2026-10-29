"""Claude Code activity as a looping scene.

Layout (52x16):
  left   spark (spins while generating, breathes while idle, sleeps with no session);
         live sub-agents orbit it as yellow satellites
  right  session count + BUSY/IDLE, and below it an equalizer (busy), a heartbeat
         line (idle) or a flat line (no session)
Hook events (see events.py) take the whole screen: DONE after a turn ends, WAIT while
Claude needs you.
"""

import glob
import math
import os
import subprocess
import time
from dataclasses import dataclass

from ..render.anim import Animation
from ..render.canvas import Canvas, dim, mix
from ..runtime import events
from . import message

PROJECTS = os.path.expanduser("~/.claude/projects")
SESSION_WINDOW = 180  # a transcript touched this recently counts as a live session
SUBAGENT_WINDOW = 40
BUSY_CPU = 8.0  # summed CPU% of `claude` processes above this = generating
BUSY_HOLD = 6.0  # stay BUSY this long after the last hot sample, so tool waits don't flicker
DONE_SECONDS = 15  # how long DONE stays up after a turn ends
WAIT_SECONDS = 600  # give up on WAIT if nobody answers for this long

ORANGE, PEACH, GREEN, WHITE = "#D97757", "#FFD9C7", "#3EE08A", "#E9EBEE"
GRAY, DARK, YELLOW = "#5B626D", "#1E242C", "#FFD000"
CX, CY = 8, 7  # spark centre
ARMS = [
    (0, -1, 4),
    (1, -1, 3),
    (1, 0, 4),
    (1, 1, 3),
    (0, 1, 4),
    (-1, 1, 3),
    (-1, 0, 4),
    (-1, -1, 3),
]
RIGHT = 20  # x where the right column starts
HEARTBEAT = {0: -1, 1: -3, 2: 2, 3: -1}  # y offsets of one beat, by x offset
ZZZ = ["###", ".#.", "###"]


@dataclass(frozen=True)
class State:
    sessions: int
    subagents: int
    busy: bool
    alert: str | None = None  # "done" or "wait" from a hook event


def claude_cpu():
    """Summed CPU% of processes whose executable is named exactly `claude`."""
    out = subprocess.run(
        ["ps", "-axo", "pcpu=,comm="], capture_output=True, text=True, timeout=5, check=True
    ).stdout
    total = 0.0
    for line in out.splitlines():
        cpu, _, comm = line.strip().partition(" ")
        if os.path.basename(comm.strip()) == "claude":
            total += float(cpu)
    return total


def count_sessions(projects, now):
    """(live sessions, live sub-agents) from transcript modification times."""
    sessions = subagents = 0
    for path in glob.glob(os.path.join(projects, "*", "*.jsonl")):
        if now - os.path.getmtime(path) > SESSION_WINDOW:
            continue
        sessions += 1
        sub_dir = os.path.join(path[: -len(".jsonl")], "subagents")
        subagents += sum(
            1
            for s in glob.glob(os.path.join(sub_dir, "*.jsonl"))
            if now - os.path.getmtime(s) < SUBAGENT_WINDOW
        )
    return sessions, subagents


class ClaudeScreen:
    """Samples Claude Code state; renders it as a GIF that only changes with the state."""

    APP = "claude"
    TICK = 2.0

    def __init__(self, projects=PROJECTS, cpu=claude_cpu, clock=time.time, event_path=None):
        self.projects, self.cpu, self.clock = projects, cpu, clock
        self.event_path = event_path or events.PATH
        self._last_hot = float("-inf")

    def sample(self):
        now = self.clock()
        sessions, subagents = count_sessions(self.projects, now)
        if sessions and self.cpu() > BUSY_CPU:
            self._last_hot = now
        busy = sessions > 0 and now - self._last_hot <= BUSY_HOLD
        return State(sessions, min(subagents, 6), busy, self._alert(now))

    def _alert(self, now):
        kind, at = events.latest(self.event_path)
        age = now - at
        if kind == "done" and age < DONE_SECONDS:
            return "done"
        # Claude generating again well after the prompt means it was answered.
        resumed = self._last_hot > at + BUSY_HOLD
        if kind == "wait" and age < WAIT_SECONDS and not resumed:
            return "wait"
        return None

    def render(self, state):
        if state.alert:
            anim = message.alert_animation(state.alert.upper(), state.alert)
            anim.key = state
            return anim
        if state.busy:
            count, delay = 16, 80
        elif state.sessions:
            count, delay = 32, 80
        else:
            count, delay = 24, 120
        frames = [_frame(state, f, count) for f in range(count)]
        return Animation(frames, delay, key=state)


def _frame(state, f, count):
    c = Canvas()
    t = f / count  # 0..1 through the loop; every motion completes whole cycles
    _spark(c, state, f, t)
    _orbit(c, state.subagents, t)
    _status(c, state)
    if state.busy:
        _equalizer(c, t)
    elif state.sessions:
        _heartbeat(c, f)
    else:
        c.rect(RIGHT, 13, 52 - RIGHT, 1, DARK)
    return c


def _spark(c, state, f, t):
    if state.busy:  # a bright head runs round the arms: reads as spinning
        head = (f // 2) % len(ARMS)
        for i, (dx, dy, length) in enumerate(ARMS):
            behind = (head - i) % len(ARMS)
            color = PEACH if behind == 0 else ORANGE if behind == 1 else dim(ORANGE, 0.55)
            _arm(c, dx, dy, length, color)
        c.set(CX, CY, PEACH)
        return
    if state.sessions:  # slow breath
        level = 0.45 + 0.55 * (0.5 - 0.5 * math.cos(2 * math.pi * t))
    else:
        level = 0.25
    for dx, dy, length in ARMS:
        _arm(c, dx, dy, length, dim(ORANGE, level))
    c.set(CX, CY, dim(ORANGE, level))
    if not state.sessions:  # a "z" drifts up and fades
        c.sprite(13, 4 - round(4 * t), ZZZ, dim(GRAY, 1 - t))


def _arm(c, dx, dy, length, color):
    for r in range(1, length + 1):
        c.set(CX + dx * r, CY + dy * r, color)


def _orbit(c, n, t):
    for k in range(n):
        a = 2 * math.pi * (t + k / n)
        for lag, shade in ((0.0, 1.0), (0.06, 0.35)):  # dot plus a faint tail
            x = round(CX + 7.5 * math.cos(a - 2 * math.pi * lag))
            y = round(CY + 6.5 * math.sin(a - 2 * math.pi * lag))
            if c.get(x, y) == 0 or shade == 1.0:
                c.set(x, y, dim(YELLOW, shade))


def _status(c, state):
    count = str(min(state.sessions, 99))
    color = GREEN if state.busy else WHITE if state.sessions else GRAY
    x = c.text(RIGHT, 1, count, color) + 2
    if state.busy:
        label, label_color = "BUSY", GREEN
    elif state.sessions:
        label, label_color = "IDLE", GRAY
    else:
        label, label_color = "OFF", GRAY
    c.text(x, 3, label, label_color, big=False)


def _equalizer(c, t):
    """Eight 3 px bars bouncing out of phase, green at the floor to yellow at the top."""
    for i in range(8):
        level = 0.5 + 0.5 * math.sin(2 * math.pi * (t * (1 + i % 3)) + i * 1.7)
        height = 1 + round(5 * level)
        for row in range(height):
            color = mix(GREEN, YELLOW, row / 5)
            c.rect(RIGHT + i * 4, 15 - row, 3, 1, color)


def _heartbeat(c, f):
    """A flat line with one beat scrolling right to left; wraps every 32 px."""
    width = 52 - RIGHT
    for x in range(width):
        offset = HEARTBEAT.get((x + f) % width - (width - 8), 0)
        if offset:  # draw the whole stroke so the spike reads as one line
            for y in range(min(13, 13 + offset), max(13, 13 + offset) + 1):
                c.set(RIGHT + x, y, GREEN)
        else:
            c.set(RIGHT + x, 13, dim(GREEN, 0.35))
