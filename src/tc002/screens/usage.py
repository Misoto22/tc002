"""Plan limits of Claude Code and Codex on one screen, one 8-pixel row per agent.

Layout of a row (52 px wide):
  x 1-5    agent mark, 5x5, in the agent's colour
  x 8-18   5-hour % used, small font ("--" when unknown); amber from 80 %, blinking from 95 %
  x 25-50  5-hour bar, 3 px tall; under it a 1 px line for the 7-day %
Claude Code is the top row (y 1), Codex the bottom (y 9). Bars fill from empty when the
screen comes on, then hold.
"""

from dataclasses import dataclass

from ..render.anim import Animation
from ..render.canvas import Canvas
from ..render.palette import LED
from ..usage.claude import ClaudeUsage
from ..usage.codex import CodexUsage

FILL_FRAMES, FILL_MS, HOLD_MS, BLINK_MS = 12, 40, 4000, 500
WARN, CRITICAL = 80, 95
BAR_X, BAR_W = 25, 26
AGENTS = {
    "claude": (LED["orange"], ["#.#.#", ".###.", "#####", ".###.", "#.#.#"]),
    "codex": (LED["teal"], [".###.", "#...#", "#.#.#", "#...#", ".###."]),
}
ROWS = (("claude", 1), ("codex", 9))


@dataclass(frozen=True)
class Row:
    agent: str
    five_hour: int | None  # % used, rounded; None when the agent has not reported it
    week: int | None


@dataclass(frozen=True)
class State:
    rows: tuple[Row, ...]


def _round(pct):
    return None if pct is None else max(0, min(100, round(pct)))


def _bar(c, y, height, pct, colour):
    c.rect(BAR_X, y, BAR_W, height, LED["track"])
    if pct:
        c.rect(BAR_X, y, max(1, round(BAR_W * pct / 100)), height, colour)


def draw_row(c, row, y, progress=1.0, lit=True):
    colour, mark = AGENTS[row.agent]
    known = row.five_hour is not None
    c.sprite(1, y, mark, colour if known else LED["gray"])
    if not known:
        c.text(8, y, "--", LED["gray"], big=False)
    elif lit:
        warn = row.five_hour >= WARN
        c.text(8, y, f"{row.five_hour}%", LED["amber"] if warn else LED["white"], big=False)
    eased = 1 - (1 - progress) ** 3
    _bar(c, y, 3, (row.five_hour or 0) * eased, colour)
    _bar(c, y + 4, 1, (row.week or 0) * eased, LED["soft_white"])


def frame(state, progress=1.0, lit=True):
    c = Canvas()
    for row, (_, y) in zip(state.rows, ROWS, strict=True):
        draw_row(c, row, y, progress, lit)
    return c


def render(state):
    frames = [frame(state, i / FILL_FRAMES) for i in range(1, FILL_FRAMES + 1)]
    delays = [FILL_MS] * (FILL_FRAMES - 1) + [HOLD_MS]
    if any(r.five_hour is not None and r.five_hour >= CRITICAL for r in state.rows):
        frames += [frame(state, lit=False), frame(state)] * 4
        delays += [BLINK_MS] * 8
    return Animation(frames, delays, key=state)


class UsageScreen:
    """Re-renders only when a rounded percentage changes."""

    APP = "usage"
    TICK = 30.0

    def __init__(self, claude=None, codex=None):
        self.claude, self.codex = claude or ClaudeUsage(), codex or CodexUsage()

    def sample(self):
        rows = []
        for agent, reader in (("claude", self.claude), ("codex", self.codex)):
            u = reader.collect()
            rows.append(Row(agent, _round(u.limit_5h), _round(u.limit_week)))
        return State(tuple(rows))

    def render(self, state):
        return render(state)
