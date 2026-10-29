"""Breakout: bounce the ball off your paddle and clear the wall of bricks.

Board 52x16: four rows of 4-pixel bricks at the top (y 1-4, a colour per row), a
6-pixel paddle on the bottom row, a 1-pixel ball. Left / right move the paddle; the ball
takes the paddle's edge to bounce sideways. Three lives.
"""

import random

from ..render.canvas import HEIGHT, WIDTH
from ..render.palette import LED

BRICK_W, ROWS = 4, ("red", "orange", "yellow", "green")
PADDLE_W, PADDLE_Y = 8, HEIGHT - 1
LIVES = 3


class Breakout:
    NAME = "breakout"
    KEYS = ("left", "right", "space")

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.score, self.lives, self.over = 0, LIVES, False
        self.bricks = {(x, 1 + r) for r in range(len(ROWS)) for x in range(0, WIDTH, BRICK_W)}
        self.paddle = (WIDTH - PADDLE_W) // 2
        self._serve()

    def _serve(self):
        self.ball = [self.paddle + PADDLE_W // 2, PADDLE_Y - 1]
        self.vel = [self.rng.choice((-1, 1)), -1]

    def step(self, pressed):
        if self.over:
            return
        if "left" in pressed:
            self.paddle = max(0, self.paddle - 2)
        if "right" in pressed:
            self.paddle = min(WIDTH - PADDLE_W, self.paddle + 2)
        x, y = self.ball[0] + self.vel[0], self.ball[1] + self.vel[1]
        if not 0 <= x < WIDTH:
            self.vel[0] *= -1
            x = self.ball[0] + self.vel[0]
        if y < 0:
            self.vel[1] = 1
            y = self.ball[1] + 1
        hit = next((b for b in self.bricks if b[1] == y and b[0] <= x < b[0] + BRICK_W), None)
        if hit:
            self.bricks.discard(hit)
            self.score += 1
            self.vel[1] *= -1
            y = self.ball[1]
        if y == PADDLE_Y:
            if self.paddle <= x < self.paddle + PADDLE_W:
                third = (x - self.paddle) * 3 // PADDLE_W  # left, middle or right of the paddle
                self.vel = [(-1, self.vel[0] or 1, 1)[third], -1]
                y = PADDLE_Y - 1
            else:
                self.lives -= 1
                self.over = self.lives == 0
                if not self.over:
                    self._serve()
                return
        self.ball = [x, y]
        if not self.bricks:
            self.over = True

    def draw(self, c):
        for bx, by in self.bricks:
            c.rect(bx, by, BRICK_W - 1, 1, LED[ROWS[by - 1]])
        c.rect(self.paddle, PADDLE_Y, PADDLE_W, 1, LED["sky"])
        c.set(*self.ball, LED["white"])
        for i in range(self.lives):
            c.set(WIDTH - 1 - i * 2, 0, LED["peach"])
