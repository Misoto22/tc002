"""GIF encoder checked by decoding with Pillow (a test-only dependency)."""

import io
import random

from PIL import Image, ImageSequence

from tc002.render import gif
from tc002.render.anim import Animation
from tc002.render.canvas import Canvas


def decode(data):
    im = Image.open(io.BytesIO(data))
    return im, [f.convert("RGB") for f in ImageSequence.Iterator(im)]


def test_round_trip_frames_delays_and_loop():
    frames = []
    for i in range(5):
        c = Canvas()
        c.rect(i * 3, 2, 4, 4, 0xD97757)
        frames.append(c)
    im, decoded = decode(Animation(frames, 80).gif())
    assert len(decoded) == 5 and im.info["loop"] == 0 and im.info["duration"] == 80
    assert decoded[2].getpixel((7, 3)) == (0xD9, 0x77, 0x57)
    assert decoded[2].getpixel((0, 3)) == (0, 0, 0)


def test_noisy_frame_exercises_code_width_growth_and_table_reset():
    rng = random.Random(7)
    palette = [rng.randrange(1 << 24) for _ in range(200)]
    px = [rng.choice(palette) for _ in range(300 * 40)]
    _, decoded = decode(gif.encode([px], 300, 40, 100))
    raw = decoded[0].tobytes()
    got = [raw[i] << 16 | raw[i + 1] << 8 | raw[i + 2] for i in range(0, len(raw), 3)]
    assert got == px


def test_more_than_256_colours_are_quantized_not_rejected():
    px = list(range(0, 0xFFFFFF, 0xFFFFFF // 2000))[: 52 * 16]
    _, decoded = decode(gif.encode([px], 52, 16, 100))
    assert decoded[0].size == (52, 16)
