"""A few seconds of each game playing itself, for previews in the UI and the README.

Each autopilot presses the keys a player would: Breakout and Pong keep the paddle under
the ball, Snake heads for the food without turning into itself. Seeds are fixed, so a
preview is the same picture every time.
"""

import random

from ..render.anim import Animation
from ..render.canvas import HEIGHT, WIDTH, Canvas
from . import GAMES
from .session import FRAME_MS

FRAMES = 60  # 6 s at the session's frame rate
SEED = 7


def _breakout(game):
    centre = game.paddle + 4
    return {"left"} if game.ball[0] < centre - 1 else {"right"} if game.ball[0] > centre else set()


def _pong(game):
    centre = game.you + 2
    return {"up"} if game.ball[1] < centre else {"down"} if game.ball[1] > centre else set()


def _snake(game):
    hx, hy = game.body[0]
    fx, fy = game.food or (hx, hy)
    wanted = []
    if fx != hx:
        wanted.append("right" if fx > hx else "left")
    if fy != hy:
        wanted.append("down" if fy > hy else "up")
    for key in [*wanted, "up", "down", "left", "right"]:
        dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}[key]
        if (dx, dy) == (-game.heading[0], -game.heading[1]):
            continue
        if ((hx + dx) % WIDTH, (hy + dy) % HEIGHT) not in game.body[:-1]:
            return {key}
    return set()


PILOTS = {"breakout": _breakout, "pong": _pong, "snake": _snake}


def demo(name, frames=FRAMES):
    """The game `name` playing itself for `frames` frames."""
    game = GAMES[name](random.Random(SEED))
    pilot = PILOTS[name]
    out = []
    for _ in range(frames):
        game.step(pilot(game))
        c = Canvas()
        game.draw(c)
        out.append(c)
        if game.over:
            game = GAMES[name](random.Random(SEED))
    return Animation(out, FRAME_MS, key=("demo", name))
