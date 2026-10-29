"""Hacker News stories, one at a time: points and comments on top, the title scrolling.

Data: the official Hacker News Firebase API (no key, no rate limit): the chosen list's
ranked ids, then each item. Stories are read every `refresh` minutes and shown in turn
(pager.py). Skipped: dead or deleted items, stories under `min_points` (not applied to
the "new" list, where nothing has points yet), and, when `keyword` is set, titles
without it. Layout: an orange Y and the story's place ("2/5"), its points and comment
count on the top row; the title on the bottom row, scrolling when it does not fit.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import ClassVar

from .. import net
from ..render import font
from ..render.anim import Animation
from ..render.palette import LED
from . import ticker
from .pager import Pager

LIST = "https://hacker-news.firebaseio.com/v0/{kind}stories.json"
ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
KINDS = ("top", "best", "new", "ask", "show")
SCAN = 30  # ids read from the list before filtering
BATCH = 12  # items read side by side; more batches only while too few stories pass


@dataclass(frozen=True)
class Story:
    title: str
    points: int
    comments: int = 0


@dataclass(frozen=True)
class State:
    story: Story
    index: int = 0
    count: int = 1


def _story(item):
    return Story(str(item["title"]), int(item.get("score", 0)), int(item.get("descendants", 0)))


def short(n):
    return f"{n / 1000:.1f}K" if n >= 1000 else str(n)


class HackerNewsScreen:
    APP = "hackernews"
    OPTIONS: ClassVar[dict] = {
        "list": ("choice", "top", KINDS),
        "count": ("int", 5, (1, 10)),
        "min_points": ("int", 100, (0, 1000)),
        "keyword": ("text", "", 24),
        "refresh": ("int", 5, (3, 30)),  # minutes
        "seconds": ("int", 12, (6, 60)),  # each story
    }

    def __init__(self, options=None, get=net.get_json, clock=None):
        o = {k: d for k, (_, d, _) in self.OPTIONS.items()} | (options or {})
        self.kind, self.count = o["list"], o["count"]
        self.min_points = 0 if o["list"] == "new" else o["min_points"]
        self.keyword = o["keyword"].casefold().strip()
        self.get = get
        self.TICK = float(min(o["seconds"], 15))
        kwargs = {"clock": clock} if clock else {}
        self.pager = Pager(self._fetch, o["refresh"] * 60, o["seconds"], **kwargs)

    def _fetch(self):
        ids = self.get(LIST.format(kind=self.kind))[:SCAN]
        stories = []
        with ThreadPoolExecutor(BATCH) as pool:
            for start in range(0, len(ids), BATCH):
                batch = ids[start : start + BATCH]
                for item in pool.map(lambda i: self.get(ITEM.format(id=i)) or {}, batch):
                    if self._keep(item):
                        stories.append(_story(item))
                if len(stories) >= self.count:
                    break
        if not stories:
            raise ValueError("no story matches the filters")
        return stories[: self.count]

    def _keep(self, item):
        title = str(item.get("title", ""))
        if item.get("dead") or item.get("deleted") or not title:
            return False
        if int(item.get("score", 0)) < self.min_points:
            return False
        return not self.keyword or self.keyword in title.casefold()

    def sample(self):
        index, count, story = self.pager.current()
        return State(story, index, count)

    def render(self, state):
        s = state.story
        table = font.for_text(s.title)
        cjk = table not in (font.BIG, font.SMALL)
        table = table if cjk else font.SMALL
        y = 3 if cjk else 10

        def static(c):
            if cjk:
                return
            c.rect(0, 0, 7, 7, LED["orange"])
            c.text(2, 1, "Y", 0, big=False)
            top = f"{short(s.points)}P {short(s.comments)}C"
            c.text(9, 1, top, LED["label"], big=False)
            place = f"{state.index + 1}/{state.count}"
            place_x = 52 - font.text_width(font.SMALL, place)
            if state.count > 1 and place_x >= 9 + font.text_width(font.SMALL, top) + 3:
                c.text(place_x, 1, place, LED["gray"], big=False)

        frames = ticker.frames(static, s.title, y, LED["white"], table)
        return Animation(frames, ticker.FRAME_MS, key=state)
