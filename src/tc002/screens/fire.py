"""A fireplace: flames rising from the bottom row, for a calm screen in the rotation.

The classic heat-spreading fire: the bottom row burns at full heat, each pixel above
takes its neighbour's heat minus a little, drifting sideways, and heat maps to colour
from dark red through orange and yellow to white.
"""

import random
from dataclasses import dataclass

from ..render.anim import Animation
from ..render.canvas import HEIGHT, WIDTH, Canvas, dim, mix
from ..render.palette import LED

FRAMES, FRAME_MS = 40, 80
HEAT = 24  # levels of heat; the bottom row is the hottest


def colour(level):
    """Heat 0..HEAT-1 to a colour: off, dark red, orange, yellow, white."""
    t = level / (HEAT - 1)
    if t < 0.15:
        return 0
    if t < 0.45:
        return dim(LED["red"], (t - 0.15) / 0.3)
    if t < 0.75:
        return mix(LED["red"], LED["orange"], (t - 0.45) / 0.3)
    if t < 0.95:
        return mix(LED["orange"], LED["yellow"], (t - 0.75) / 0.2)
    return LED["peach"]


@dataclass(frozen=True)
class State:
    seed: int = 0


class FireScreen:
    APP = "fire"
    TICK = 3600.0

    def __init__(self, options=None):
        pass

    def sample(self):
        return State()

    def render(self, state):
        rng = random.Random(state.seed)
        heat = [[0] * WIDTH for _ in range(HEIGHT)]
        heat[-1] = [HEAT - 1] * WIDTH
        frames = []
        for f in range(FRAMES + HEIGHT):  # let the flames build before recording
            nxt = [row[:] for row in heat]
            for y in range(HEIGHT - 1):
                for x in range(WIDTH):
                    src = heat[y + 1][(x + rng.randint(-1, 1)) % WIDTH]
                    nxt[y][x] = max(0, src - rng.randint(0, 3))
            heat = nxt
            if f >= HEIGHT:
                c = Canvas()
                for y in range(HEIGHT):
                    for x in range(WIDTH):
                        if heat[y][x]:
                            c.set(x, y, colour(heat[y][x]))
                frames.append(c)
        return Animation(frames, FRAME_MS, key=state)
