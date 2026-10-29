"""Snake: steer with the arrow keys, eat the food, do not run into yourself.

The board wraps at the edges. The snake moves one cell every other frame and grows by
one for each food; the head is bright green, the body fades along its length.
"""

import random

from ..render.canvas import HEIGHT, WIDTH, dim
from ..render.palette import LED

TURNS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
EVERY = 2  # frames per move


class Snake:
    NAME = "snake"
    KEYS = ("up", "down", "left", "right", "space")

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        mid = (WIDTH // 2, HEIGHT // 2)
        self.body = [mid, (mid[0] - 1, mid[1]), (mid[0] - 2, mid[1])]
        self.heading, self.score, self.over, self._tick = (1, 0), 0, False, 0
        self._place_food()

    def _place_food(self):
        free = [(x, y) for x in range(WIDTH) for y in range(HEIGHT) if (x, y) not in self.body]
        self.food = self.rng.choice(free) if free else None

    def step(self, pressed):
        if self.over:
            return
        for key in pressed:  # turn, but never straight back into the neck
            dx, dy = TURNS.get(key, self.heading)
            if (dx, dy) != (-self.heading[0], -self.heading[1]):
                self.heading = (dx, dy)
        self._tick += 1
        if self._tick % EVERY:
            return
        head = (
            (self.body[0][0] + self.heading[0]) % WIDTH,
            (self.body[0][1] + self.heading[1]) % HEIGHT,
        )
        if head in self.body[:-1]:
            self.over = True
            return
        self.body.insert(0, head)
        if head == self.food:
            self.score += 1
            self._place_food()
        else:
            self.body.pop()

    def draw(self, c):
        if self.food:
            c.set(*self.food, LED["red"])
        n = len(self.body)
        for i, (x, y) in enumerate(self.body):
            c.set(x, y, LED["green"] if i == 0 else dim(LED["teal"], 1 - 0.6 * i / n))
