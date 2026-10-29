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
# social apps: each one's mark as 12x12 pixel art, then a follower count. Letters map to
# palette colours (ICON_COLOURS); "." is off.
ICON_COLOURS = {
    "r": "red",
    "w": "white",
    "b": "blue",
    "s": "sky",
    "c": "cyan",
    "v": "violet",
    "o": "orange",
    "y": "yellow",
    "p": "peach",
    "g": "gray",
}
SOCIAL = {
    "youtube": [
        "............",
        ".rrrrrrrrrr.",
        "rrrrrrrrrrrr",
        "rrrrrwrrrrrr",
        "rrrrrwwrrrrr",
        "rrrrrwwwrrrr",
        "rrrrrwwrrrrr",
        "rrrrrwrrrrrr",
        "rrrrrrrrrrrr",
        ".rrrrrrrrrr.",
        "............",
        "............",
    ],
    "facebook": [
        ".bbbbbbbbbb.",
        "bbbbbbbbbbbb",
        "bbbbbbbwwwbb",
        "bbbbbbwbbbbb",
        "bbbbbbwbbbbb",
        "bbbbwwwwwbbb",
        "bbbbbbwbbbbb",
        "bbbbbbwbbbbb",
        "bbbbbbwbbbbb",
        "bbbbbbwbbbbb",
        "bbbbbbwbbbbb",
        ".bbbbbwbbbb.",
    ],
    "instagram": [
        ".vvvvvvvvvv.",
        "v..........v",
        "v........v.v",
        "v...vvvv...v",
        "v..v....v..v",
        "o..o....o..o",
        "o..o....o..o",
        "o...oooo...o",
        "o..........o",
        "y..........y",
        ".yyyyyyyyyy.",
        "............",
    ],
    "bilibili": [
        "..s......s..",
        "...s....s...",
        "....s..s....",
        ".ssssssssss.",
        "s..........s",
        "s..s....s..s",
        "s..s....s..s",
        "s..........s",
        "s...s..s...s",
        "s....ss....s",
        ".ssssssssss.",
        "............",
    ],
    "weibo": [
        ".........oo.",
        "..........o.",
        "...rrrrr....",
        "..rrrrrrr...",
        ".rrr.y.rrr..",
        ".rr.yyy.rr..",
        ".rrr.y.rrr..",
        "..rrrrrrr...",
        "...rrrrr....",
        "............",
        "............",
        "............",
    ],
    "xhs": [
        ".rrrrrrrrrr.",
        "rrrrrrrrrrrr",
        "rrrrrrrrrrrr",
        "rwwrwwwrwwrr",
        "rwrrwrrrwrwr",
        "rwwrwwrrwrwr",
        "rwrwwrrrwrwr",
        "rwrrwwwrwwrr",
        "rrrrrrrrrrrr",
        "rrrrrrrrrrrr",
        ".rrrrrrrrrr.",
        "............",
    ],
    "x": [
        "ww........ww",
        ".ww......ww.",
        "..ww....ww..",
        "...ww..ww...",
        "....wwww....",
        ".....ww.....",
        "....wwww....",
        "...ww..ww...",
        "..ww....ww..",
        ".ww......ww.",
        "ww........ww",
        "............",
    ],
}
NOTE = [
    "......##....",
    "......#.#...",
    "......#..#..",
    "......#.....",
    "......#.....",
    "......#.....",
    "...####.....",
    "..#####.....",
    "..####......",
    "............",
]
SOCIAL_NOTE = {"douyin", "tiktok"}  # the note mark: cyan and red shadows under white


def _icon(c, x, y, rows):
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch != ".":
                c.set(x + dx, y + dy, LED[ICON_COLOURS[ch]])


def _note(c, x, y):
    for colour, (ox, oy) in (("cyan", (-1, -1)), ("red", (1, 1)), ("white", (0, 0))):
        for dy, row in enumerate(NOTE):
            for dx, ch in enumerate(row):
                if ch == "#":
                    c.set(x + dx + ox, y + dy + oy, LED[colour])


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
    if key in SOCIAL_NOTE:
        _note(c, 1, 3)
    else:
        _icon(c, 1, 2, SOCIAL[key])
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
