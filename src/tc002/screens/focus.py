"""A focus timer (Pomodoro): minutes of work, then a short break, counting down.

Start it from the UI or `tc002 focus start`; the state lives in runtime/focus.py.
Idle, it shows FOCUS and the length of a session. Running, the time left ticks down
second by second (each GIF covers the next MAX_FRAMES seconds) above a bar that empties;
work is amber, the break green.
"""

import time
from dataclasses import dataclass
from typing import ClassVar

from ..render import font
from ..render.anim import MAX_FRAMES, Animation
from ..render.canvas import WIDTH, Canvas
from ..render.palette import LED
from ..runtime import focus

BAR_Y = 14


@dataclass(frozen=True)
class State:
    phase: str  # "idle", "focus" or "break"
    left: int  # whole seconds left in this phase
    total: int  # seconds in this phase


class FocusScreen:
    APP = "focus"
    TICK = 20.0
    OPTIONS: ClassVar[dict] = {
        "minutes": ("int", 25, (5, 90)),
        "break_minutes": ("int", 5, (1, 30)),
    }

    def __init__(self, options=None, clock=time.time, path=None):
        options = options or {}
        self.minutes = options.get("minutes", 25)
        self.break_minutes = options.get("break_minutes", 5)
        self.clock, self.path = clock, path

    def sample(self):
        now = focus.current(self.path, self.clock())
        if now is None:
            return State("idle", self.minutes * 60, self.minutes * 60)
        phase, left = now
        total = (self.minutes if phase == "focus" else self.break_minutes) * 60
        return State(phase, int(left), total)

    def _frame(self, state, left):
        c = Canvas()
        colour = LED["green"] if state.phase == "break" else LED["amber"]
        if state.phase == "idle":
            c.text(1, 1, "FOCUS", LED["label"], big=False)
            colour = LED["gray"]
        else:
            c.text(1, 1, "BREAK" if state.phase == "break" else "FOCUS", colour, big=False)
        text = f"{left // 60:02d}:{left % 60:02d}"
        c.text(
            WIDTH - font.text_width(font.BIG, text) - 1,
            1,
            text,
            LED["white"] if state.phase != "idle" else LED["gray"],
        )
        c.rect(1, BAR_Y, WIDTH - 2, 1, LED["track"])
        c.rect(1, BAR_Y, max(1, round((WIDTH - 2) * left / max(1, state.total))), 1, colour)
        return c

    def render(self, state):
        if state.phase == "idle":
            return Animation.still(self._frame(state, state.left), key=state)
        count = min(MAX_FRAMES, state.left + 1)
        frames = [self._frame(state, max(0, state.left - i)) for i in range(count)]
        return Animation(frames, 1000, key=state)
