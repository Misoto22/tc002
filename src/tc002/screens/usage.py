"""Token usage of Claude Code and Codex, one page per agent.

Layout of a page (52x16):
  [icon 7x7]  NAME (agent colour)            5h tokens (top right, grey)
              TODAY'S TOKENS (big, counts up when the page appears)
              5h / weekly allowance bars (bottom row, Codex only, when reported)
"""

from dataclasses import dataclass

from .. import usage as tokens
from ..render import font
from ..render.anim import Animation
from ..render.canvas import WIDTH, Canvas, mix
from ..render.palette import LED
from ..usage.claude import ClaudeUsage
from ..usage.codex import CodexUsage

COUNT_FRAMES, COUNT_MS, HOLD_MS = 7, 45, 3500
# name, colour and a 7x7 mark per agent (Claude's spark; a prompt-in-a-ring for Codex)
AGENTS = {
    "claude": (
        "CLAUDE",
        LED["orange"],
        ["...#...", ".#.#.#.", "..###..", "#######", "..###..", ".#.#.#.", "...#..."],
    ),
    "codex": (
        "CODEX",
        LED["teal"],
        [".#####.", "##...##", "#.#....", "#..#...", "#.#....", "##...##", ".#####."],
    ),
}


@dataclass(frozen=True)
class Page:
    agent: str
    today: int
    window: int
    limit_5h: float | None = None
    limit_week: float | None = None


def load_color(pct):
    return (
        mix(LED["green"], LED["yellow"], pct / 60)
        if pct <= 60
        else mix(LED["yellow"], LED["red"], (pct - 60) / 40)
    )


def draw_page(c, page, progress=1.0):
    """Draw one agent's numbers; `progress` (0..1) animates the count-up."""
    name, colour, icon = AGENTS[page.agent]
    c.sprite(1, 4, icon, colour)
    c.text(11, 1, name, colour, big=False)
    window = tokens.short(page.window)
    c.text(WIDTH - font.text_width(font.SMALL, window), 1, window, LED["label"], big=False)
    eased = 1 - (1 - progress) ** 3
    c.text(11, 8, tokens.short(page.today * eased), LED["white"])
    for x0, pct in ((11, page.limit_5h), (32, page.limit_week)):
        if pct is not None:
            c.rect(x0, 15, 19, 1, LED["track"])
            c.rect(x0, 15, max(1, round(19 * min(pct, 100) / 100)), 1, load_color(pct))


def page_frames(page):
    """Count-up frames followed by one long hold."""
    frames = []
    for i in range(1, COUNT_FRAMES + 1):
        c = Canvas()
        draw_page(c, page, i / COUNT_FRAMES)
        frames.append(c)
    return frames, [COUNT_MS] * (COUNT_FRAMES - 1) + [HOLD_MS]


@dataclass(frozen=True)
class State:
    pages: tuple[Page, ...]


class UsageScreen:
    """Claude Code and Codex token usage; re-renders only when a rounded number changes."""

    APP = "usage"
    TICK = 30.0

    def __init__(self, claude=None, codex=None):
        self.claude, self.codex = claude or ClaudeUsage(), codex or CodexUsage()

    def sample(self):
        pages = []
        c = self.claude.collect()
        pages.append(Page("claude", tokens.rough(c.today), tokens.rough(c.window)))
        x = self.codex.collect()
        if x.source != "none":  # only show Codex when it is installed
            pages.append(
                Page(
                    "codex", tokens.rough(x.today), tokens.rough(x.window), x.limit_5h, x.limit_week
                )
            )
        return State(tuple(pages))

    def render(self, state):
        return render(state)


def render(state):
    """All pages back to back, keyed on the numbers shown."""
    frames, delays = [], []
    for page in state.pages:
        f, d = page_frames(page)
        frames += f
        delays += d
    return Animation(frames, delays, key=state)
