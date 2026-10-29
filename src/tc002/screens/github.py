"""Your GitHub at a glance: reviews waiting on you, your open pull requests, and unread
notifications, as three counts.

Data: the GitHub CLI (`gh`), already signed in on this Mac; tc002 holds no token. A
missing or signed-out `gh` shows as no data, with the reason in the UI.
"""

import json
import subprocess
from dataclasses import dataclass

from ..render import font
from ..render.anim import Animation
from ..render.canvas import Canvas
from ..render.palette import LED

COLUMNS = (
    (0, 17, "REV", "amber", "reviews"),
    (18, 17, "PRS", "sky", "mine"),
    (36, 16, "NEW", "violet", "unread"),
)
QUERIES = {
    "reviews": [
        "api",
        "search/issues?q=is:pr+is:open+review-requested:@me",
        "--jq",
        ".total_count",
    ],
    "mine": ["api", "search/issues?q=is:pr+is:open+author:@me", "--jq", ".total_count"],
    "unread": ["api", "notifications", "--jq", "length"],
}


def gh(args):
    done = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=20, check=True)
    return json.loads(done.stdout or "0")


@dataclass(frozen=True)
class State:
    reviews: int
    mine: int
    unread: int


class GitHubScreen:
    APP = "github"
    TICK = 300.0

    def __init__(self, options=None, run=gh):
        self.run = run

    def sample(self):
        return State(**{key: int(self.run(args)) for key, args in QUERIES.items()})

    def render(self, state):
        c = Canvas()
        for x0, width, label, colour, key in COLUMNS:
            n = getattr(state, key)
            text = str(n) if n < 100 else "99+"
            table = font.BIG if n < 100 else font.SMALL
            x = x0 + (width - font.text_width(table, text)) // 2
            c.text(x, 1, text, LED[colour] if n else LED["gray"], table=table)
            c.text(
                x0 + (width - font.text_width(font.SMALL, label)) // 2,
                10,
                label,
                LED["label"],
                big=False,
            )
        for x in (17, 35):
            c.rect(x, 2, 1, 12, LED["dim"])
        return Animation.still(c, key=state)
