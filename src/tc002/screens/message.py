"""Text animations: a shimmering or scrolling line, and alerts with chasing border lights.

Latin text uses the 5x7 font; any line with Chinese (or other characters it lacks) is
drawn whole in the 12 px CJK font, vertically centred.
"""

from ..render import font
from ..render.anim import MAX_FRAMES, Animation
from ..render.canvas import HEIGHT, WIDTH, Canvas, dim, mix
from ..render.palette import LED, MESSAGE_COLORS

COLORS = {name: f"#{LED[name]:06X}" for name in MESSAGE_COLORS}
MAX_CHARS = 60
ALERT_MAX_CHARS = 12  # an alert's text sits beside its icon
SCROLL_MS, SCROLL_STEP = 60, 2  # marquee speed: 2 px every 60 ms
SHIMMER_MS, ALERT_MS = 60, 90

# Alert kinds: colour plus a 7x7 icon drawn left of the text.
ICONS = {
    "done": (
        LED["green"],
        ["......#", ".....##", "#...##.", "##.##..", ".###...", "..#....", "......."],
    ),
    "wait": (
        LED["orange"],
        [".#####.", "#.....#", "....##.", "...#...", "...#...", ".......", "...#..."],
    ),
    "error": (
        LED["red"],
        ["...#...", "..#.#..", "..#.#..", ".#.#.#.", ".#...#.", "#..#..#", "#######"],
    ),
}


def color_of(name):
    return COLORS.get(name, name)


def fits(text, room=WIDTH - 2):
    return font.text_width(font.for_text(text), text) <= room


def _baseline(table):
    return (HEIGHT - font.height(table)) // 2


def _shine(c, x0, x1, amount):
    """Lighten lit pixels between columns x0 and x1 towards white."""
    for x in range(max(0, x0), min(WIDTH, x1)):
        for y in range(HEIGHT):
            p = c.get(x, y)
            if p:
                c.set(x, y, mix(p, LED["white"], amount))


def text_animation(text, color):
    """Animations to play in order (each within the clock's GIF limits).

    Short text: one looping animation where a light band sweeps across, then rests.
    Long text: a marquee cut into segments of at most MAX_FRAMES frames, because the
    clock rejects longer GIFs; the caller pushes them back to back.
    """
    text = text[:MAX_CHARS]
    color = color_of(color)
    table = font.for_text(text)
    y = _baseline(table)
    width = font.text_width(table, text)
    if fits(text):
        x0 = (WIDTH - width) // 2
        frames = []
        for step in range(-6, width + 6, 2):
            c = Canvas()
            c.text(x0, y, text, color, table=table)
            _shine(c, x0 + step, x0 + step + 4, 0.7)
            frames.append(c)
        rest = Canvas()
        rest.text(x0, y, text, color, table=table)
        return [Animation([*frames, rest], [SHIMMER_MS] * len(frames) + [2500])]
    frames = []
    for x in range(WIDTH, -width - SCROLL_STEP, -SCROLL_STEP):  # ends fully off-screen
        c = Canvas()
        c.text(x, y, text, color, table=table)
        frames.append(c)
    return [
        Animation(frames[i : i + MAX_FRAMES], SCROLL_MS) for i in range(0, len(frames), MAX_FRAMES)
    ]


def _perimeter():
    """Border pixels in clockwise order, starting top-left."""
    top = [(x, 0) for x in range(WIDTH)]
    right = [(WIDTH - 1, y) for y in range(1, HEIGHT)]
    bottom = [(x, HEIGHT - 1) for x in range(WIDTH - 2, -1, -1)]
    left = [(0, y) for y in range(HEIGHT - 2, 0, -1)]
    return top + right + bottom + left


def alert_animation(text, kind="done", color=None):
    """Theatre-marquee lights chase round the border; the icon and text pulse."""
    base, icon = ICONS.get(kind, ICONS["done"])
    base = color_of(color) if color else base
    text = text[:ALERT_MAX_CHARS]
    table = font.for_text(text)
    if table is font.BIG and not fits(text, WIDTH - 14):
        table = font.SMALL
    width = font.text_width(table, text)
    x = (WIDTH - (7 + 3 + width)) // 2
    ring = _perimeter()
    frames = []
    for f in range(6):
        c = Canvas()
        for i, (px, py) in enumerate(ring):
            phase = (i + f) % 6
            c.set(px, py, base if phase < 2 else dim(base, 0.25) if phase < 4 else 0)
        pulse = 0.7 + 0.3 * (1 - abs(f - 3) / 3)
        c.sprite(x, 4, icon, dim(base, pulse))
        c.text(x + 10, _baseline(table), text, dim(base, pulse), table=table)
        frames.append(c)
    return Animation(frames, ALERT_MS)
