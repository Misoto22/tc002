"""One frame of a game as the clock shows it, game-over banner included, and how often
a frame is drawn. Used by the live session (runtime/game.py) and the demos."""

from ..render import font
from ..render.canvas import HEIGHT, WIDTH, Canvas
from ..render.palette import LED

FRAME_MS = 100  # a full 52x16 bitmap takes ~60 ms to push, so 10 frames/s leaves headroom


def draw(game, name):
    c = Canvas()
    game.draw(c)
    if game.over:
        c.rect(0, 4, WIDTH, HEIGHT - 4, 0)
        c.text_centered(
            5,
            "GAME OVER" if name != "breakout" or game.bricks else "CLEARED",
            LED["white"],
            big=False,
        )
        score = f"SCORE {game.score}"
        c.text(
            (WIDTH - font.text_width(font.SMALL, score)) // 2, 11, score, LED["amber"], big=False
        )
    return c
