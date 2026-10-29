"""Conway's Game of Life across the whole display, as an ambient animation.

The board wraps at the edges. A fresh random board is seeded every `reseed` minutes (and
whenever one dies out); cells that have just been born glow brighter than old ones.
Options: how fast generations pass, how full a new board starts, and the colour.
"""

import random
import time
from dataclasses import dataclass
from typing import ClassVar

from ..render.anim import MAX_FRAMES, Animation
from ..render.canvas import HEIGHT, WIDTH, Canvas, dim
from ..render.palette import LED

SPEEDS = {"slow": 260, "normal": 160, "fast": 90}  # ms per generation
COLOURS = {
    "green": ("green", "teal"),
    "amber": ("yellow", "amber"),
    "blue": ("cyan", "sky"),
    "violet": ("peach", "violet"),
}  # newborn, then fading to


@dataclass(frozen=True)
class State:
    seed: int


def step(cells):
    """One generation on a wrapping WIDTH x HEIGHT board (a set of (x, y))."""
    counts = {}
    for x, y in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    key = ((x + dx) % WIDTH, (y + dy) % HEIGHT)
                    counts[key] = counts.get(key, 0) + 1
    return {c for c, n in counts.items() if n == 3 or (n == 2 and c in cells)}


class LifeScreen:
    APP = "life"
    TICK = 60.0
    OPTIONS: ClassVar[dict] = {
        "speed": ("choice", "normal", tuple(SPEEDS)),
        "density": ("int", 30, (10, 60)),  # % of cells alive on a new board
        "colour": ("choice", "green", tuple(COLOURS)),
        "reseed": ("int", 10, (1, 60)),  # minutes
    }

    def __init__(self, options=None, clock=time.time):
        o = {k: d for k, (_, d, _) in self.OPTIONS.items()} | (options or {})
        self.frame_ms, self.density = SPEEDS[o["speed"]], o["density"] / 100
        self.born, self.old = (LED[n] for n in COLOURS[o["colour"]])
        self.reseed = o["reseed"] * 60
        self.clock = clock

    def sample(self):
        return State(int(self.clock() // self.reseed))

    def render(self, state):
        rng = random.Random(state.seed)
        density = self.density

        def seed():
            return {(x, y) for x in range(WIDTH) for y in range(HEIGHT) if rng.random() < density}

        cells = seed()
        frames, age = [], {}
        for _ in range(MAX_FRAMES):
            if not cells:  # died out: reseed, so the loop never goes dark
                cells = seed()
            age = {c: age.get(c, 0) + 1 for c in cells}
            c = Canvas()
            for (x, y), a in age.items():
                c.set(x, y, self.born if a == 1 else dim(self.old, max(0.35, 1 - a / 12)))
            frames.append(c)
            cells = step(cells)
        return Animation(frames, self.frame_ms, key=state)
