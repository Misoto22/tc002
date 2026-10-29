"""Conway's Game of Life across the whole display, as an ambient animation.

The board wraps at the edges. A fresh random board is seeded every ten minutes (and
whenever one dies out); cells that have just been born glow brighter than old ones.
"""

import random
import time
from dataclasses import dataclass

from ..render.anim import MAX_FRAMES, Animation
from ..render.canvas import HEIGHT, WIDTH, Canvas, dim
from ..render.palette import LED

FRAME_MS = 160
DENSITY = 0.3
RESEED = 600  # seconds


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

    def __init__(self, options=None, clock=time.time):
        self.clock = clock

    def sample(self):
        return State(int(self.clock() // RESEED))

    def render(self, state):
        rng = random.Random(state.seed)

        def seed():
            return {(x, y) for x in range(WIDTH) for y in range(HEIGHT) if rng.random() < DENSITY}

        cells = seed()
        frames, age = [], {}
        for _ in range(MAX_FRAMES):
            if not cells:  # died out: reseed, so the loop never goes dark
                cells = {
                    (x, y) for x in range(WIDTH) for y in range(HEIGHT) if rng.random() < DENSITY
                }
            age = {c: age.get(c, 0) + 1 for c in cells}
            c = Canvas()
            for (x, y), a in age.items():
                c.set(x, y, LED["green"] if a == 1 else dim(LED["teal"], max(0.35, 1 - a / 12)))
            frames.append(c)
            cells = step(cells)
        return Animation(frames, FRAME_MS, key=state)
