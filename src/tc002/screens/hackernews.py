"""The top story on Hacker News: its points, and its title scrolling past.

Data: the official Hacker News Firebase API (no key).
"""

from dataclasses import dataclass

from .. import net
from ..render import font
from ..render.anim import Animation
from ..render.palette import LED
from . import ticker

TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


@dataclass(frozen=True)
class State:
    title: str
    points: int


class HackerNewsScreen:
    APP = "hackernews"
    TICK = 600.0

    def __init__(self, options=None, get=net.get_json):
        self.get = get

    def sample(self):
        story = self.get(ITEM.format(id=self.get(TOP)[0]))
        return State(str(story.get("title", "")), int(story.get("score", 0)))

    def render(self, state):
        table = font.for_text(state.title)
        cjk = table not in (font.BIG, font.SMALL)
        table = table if cjk else font.SMALL
        y = 3 if cjk else 9

        def static(c):
            if not cjk:
                c.rect(0, 0, 9, 7, LED["orange"])
                c.text(2, 1, "Y", 0, big=False)
                c.text(12, 1, f"{state.points} POINTS", LED["label"], big=False)

        frames = ticker.frames(static, state.title, y, LED["white"], table)
        return Animation(frames, ticker.FRAME_MS, key=state)
