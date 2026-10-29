"""What a screen shows when its data stops coming: how old it is, then that there is none.

A screen whose source fails (a command errors, a file vanishes, a network is down) keeps
its last picture with the data's age in the top-right corner. After NO_DATA_AFTER it is
replaced by NO DATA and how long ago the last good sample was, so an old number is never
mistaken for a current one.

Layout of the age tag: a black box behind a 3x5 label ("45S", "5M", "2H") at the top
right, so it reads over any picture. NO DATA: an unplugged-cable mark in amber at the
left, "NO DATA" in white and the age (or the screen's name) in grey to its right.
"""

from ..render import font
from ..render.anim import Animation
from ..render.canvas import WIDTH, Canvas
from ..render.palette import LED

STALE_AFTER = 30  # seconds of failed samples before the age shows
NO_DATA_AFTER = 600  # and before the old picture is withdrawn
UNPLUGGED = ["..#.#..", "..#.#..", ".#####.", ".#####.", "..###..", "...#...", "...#..."]
TEXT_X = 12


def age_label(seconds):
    """45 -> "45S", 300 -> "5M", 7200 -> "2H"; short enough for the clock's small font."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}S"
    if seconds < 3600:
        return f"{seconds // 60}M"
    return f"{seconds // 3600}H"


def mark(anim, age):
    """The same animation with the data's age in the top-right corner of every frame."""
    label = age_label(age)
    width = font.text_width(font.SMALL, label)
    x = WIDTH - width - 1
    frames = []
    for frame in anim.frames:
        c = Canvas()
        c.px = list(frame.px)
        c.rect(x - 1, 0, width + 2, 7, 0)
        c.text(x, 1, label, LED["amber"], big=False)
        frames.append(c)
    return Animation(frames, anim.delays(), key=("stale", anim.key, label))


def no_data(name, age=None):
    """NO DATA, with how long ago the last good sample was (or the screen's name)."""
    c = Canvas()
    c.sprite(2, 4, UNPLUGGED, LED["amber"])
    c.text(TEXT_X, 2, "NO DATA", LED["white"], big=False)
    detail = f"{age_label(age)} AGO" if age is not None else name.upper()[:9]
    c.text(TEXT_X, 9, detail, LED["label"], big=False)
    return Animation.still(c, key=("no-data", name, detail))
