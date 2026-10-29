"""Pong against the clock: your paddle on the left (up / down), its paddle on the right.

First to five points wins. The clock's paddle follows the ball a little slower than the
ball moves, so it can be beaten.
"""

import random

from ..render.canvas import HEIGHT, WIDTH
from ..render.palette import LED

PADDLE_H, WIN = 5, 5


class Pong:
    NAME = "pong"
    KEYS = ("up", "down", "space")

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.you = self.it = (HEIGHT - PADDLE_H) // 2
        self.points = [0, 0]
        self.over, self._tick = False, 0
        self._serve(self.rng.choice((-1, 1)))

    @property
    def score(self):
        return self.points[0]

    def _serve(self, direction):
        self.ball = [WIDTH // 2, HEIGHT // 2]
        self.vel = [direction, self.rng.choice((-1, 1))]

    def step(self, pressed):
        if self.over:
            return
        if "up" in pressed:
            self.you = max(0, self.you - 1)
        if "down" in pressed:
            self.you = min(HEIGHT - PADDLE_H, self.you + 1)
        self._tick += 1
        if self._tick % 3 == 0:  # the clock's paddle is slower than the ball
            centre = self.it + PADDLE_H // 2
            self.it += (self.ball[1] > centre) - (self.ball[1] < centre)
            self.it = max(0, min(HEIGHT - PADDLE_H, self.it))
        x, y = self.ball[0] + self.vel[0], self.ball[1] + self.vel[1]
        if not 0 <= y < HEIGHT:
            self.vel[1] *= -1
            y = self.ball[1] + self.vel[1]
        for paddle_x, top, back in ((1, self.you, 1), (WIDTH - 2, self.it, -1)):
            if x == paddle_x and top <= y < top + PADDLE_H:
                self.vel[0] = back
                x = self.ball[0] + back
        if x < 0 or x >= WIDTH:
            winner = 1 if x < 0 else 0
            self.points[winner] += 1
            self.over = max(self.points) >= WIN
            self._serve(1 if winner else -1)
            return
        self.ball = [x, y]

    def draw(self, c):
        for y in range(0, HEIGHT, 2):
            c.set(WIDTH // 2, y, LED["dim"])
        c.rect(1, self.you, 1, PADDLE_H, LED["sky"])
        c.rect(WIDTH - 2, self.it, 1, PADDLE_H, LED["orange"])
        c.text(WIDTH // 2 - 6, 0, str(self.points[0]), LED["sky"], big=False)
        c.text(WIDTH // 2 + 4, 0, str(self.points[1]), LED["orange"], big=False)
        c.set(*self.ball, LED["white"])
