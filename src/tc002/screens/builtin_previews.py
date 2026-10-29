"""Approximate stills of the clock's built-in apps, for the UI's rotation previews.

The firmware draws these itself and offers no way to read them back, so each is a close
imitation at 52x16 with tc002's fonts: what the app shows, not its exact pixels. The UI
labels them as approximate.
"""

from .. import builtins
from ..render.anim import Animation
from ..render.canvas import Canvas
from ..render.palette import LED

SUN = ["....#....", ".#.....#.", "...###...", "#.#####.#", "...###...", ".#.....#.", "....#...."]
TOMATO = ["...#...", ".#####.", "#######", "#######", "#######", ".#####.", "..###.."]
HOLD_MS = 4000
# social apps: two-letter tag and the colour of their mark
SOCIAL = {
    "xhs": ("XH", "red"),
    "douyin": ("DY", "cyan"),
    "bilibili": ("BL", "sky"),
    "weibo": ("WB", "orange"),
    "youtube": ("YT", "red"),
    "instagram": ("IG", "violet"),
    "facebook": ("FB", "blue"),
    "tiktok": ("TT", "cyan"),
    "x": ("X", "white"),
}


def _clock(c):
    c.text_centered(2, "14:32", LED["white"])
    for i in range(7):
        c.rect(5 + i * 6, 13, 5, 1, LED["white"] if i == 3 else LED["dim"])


def _weather(c):
    c.sprite(3, 4, SUN, LED["yellow"])
    c.text(17, 1, "18C", LED["white"])
    c.text(17, 10, "SUNNY", LED["label"], big=False)


def _tomato(c):
    c.sprite(2, 4, TOMATO, LED["red"])
    c.text(14, 4, "25:00", LED["white"])


def _stopwatch(c):
    c.text_centered(4, "00:42", LED["white"])


def _scoreboard(c):
    c.text(4, 4, "3", LED["sky"])
    c.text_centered(4, ":", LED["label"])
    c.text(43, 4, "2", LED["red"])


def _battery(c):
    c.rect(10, 4, 28, 9, LED["label"])
    c.rect(11, 5, 26, 7, 0)
    c.rect(12, 6, 18, 5, LED["green"])
    c.rect(38, 7, 2, 3, LED["label"])


def _busy(c):
    c.text_centered(4, "BUSY", LED["red"])


def _soundlight(c):
    for i, level in enumerate((3, 6, 9, 5, 11, 7, 4, 8, 10, 6, 3, 5)):
        c.rect(3 + i * 4, 15 - level, 3, level, LED["violet"])


def _ipshow(c):
    c.text_centered(5, "192.168.4.100", LED["white"], big=False)


def _social(c, key):
    tag, colour = SOCIAL[key]
    c.rect(1, 2, 13, 12, LED[colour])
    c.text(2 if len(tag) == 2 else 6, 6, tag, 0, big=False)
    c.text(18, 4, "12.4K", LED["white"])


def _calendar(c):
    c.text(1, 1, "10:30", LED["orange"], big=False)
    c.text(1, 9, "STANDUP", LED["white"], big=False)
    c.rect(48, 1, 3, 3, LED["orange"])


TOOLS = {
    "clock": _clock,
    "weather": _weather,
    "tomato": _tomato,
    "stopwatch": _stopwatch,
    "scoreboard": _scoreboard,
    "battery": _battery,
    "busy": _busy,
    "soundlight": _soundlight,
    "ipshow": _ipshow,
}


def render(key):
    """A one-frame Animation imitating built-in app `key`."""
    app = builtins.lookup(key)
    c = Canvas()
    if app.category == "tools":
        TOOLS[key](c)
    elif app.category == "social":
        _social(c, key)
    else:
        _calendar(c)
    return Animation([c], [HOLD_MS])
