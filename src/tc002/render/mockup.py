"""LED-style mock-ups: each device pixel drawn as a round lamp, for previews and docs."""

from . import gif
from .canvas import HEIGHT, WIDTH
from .palette import LED

CELL = 8
BG, OFF = LED["panel"], LED["off"]


def _lamp_mask():
    r = CELL / 2 - 0.7
    centre = CELL / 2 - 0.5
    return [
        [(dx - centre) ** 2 + (dy - centre) ** 2 <= r * r for dx in range(CELL)]
        for dy in range(CELL)
    ]


_MASK = _lamp_mask()


def led_pixels(px):
    """Upscale one 52x16 frame to (52*CELL)x(16*CELL) lamps."""
    w = WIDTH * CELL
    out = [BG] * (w * HEIGHT * CELL)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            color = px[y * WIDTH + x] or OFF
            for dy, row in enumerate(_MASK):
                base = (y * CELL + dy) * w + x * CELL
                for dx, on in enumerate(row):
                    if on:
                        out[base + dx] = color
    return out


def led_gif(anim):
    frames = [led_pixels(f.px) for f in anim.frames]
    return gif.encode(frames, WIDTH * CELL, HEIGHT * CELL, anim.delays())
