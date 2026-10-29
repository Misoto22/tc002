"""One game being played: a loop that steps the game, draws it, and puts each frame on
the clock as a `draw` bitmap, while the browser sends key presses and mirrors the frame.

Frames go out every FRAME_MS (a full 52x16 bitmap takes ~60 ms to push on this
repository's clock, so 10 frames/s leaves headroom). While a session runs, the rotation
is held so it does not switch away; stopping removes the game's app and lets go.
"""

import contextlib
import random
import threading
import time

from ..device import DeviceError
from ..render import font, themes
from ..render.canvas import HEIGHT, WIDTH, Canvas
from ..render.palette import LED
from ..runtime import hold
from . import GAMES

APP = "tc002-game"
FRAME_MS = 100
IDLE_STOP = 120  # seconds without a key press before the game gives the clock back


class Session:
    def __init__(self, device, name, theme=themes.CLASSIC, clock=time.monotonic):
        if name not in GAMES:
            raise ValueError(f"unknown game {name!r}; known: {', '.join(GAMES)}")
        self.device, self.name, self.theme, self.clock = device, name, theme, clock
        self.game = GAMES[name](random.Random())
        self._held, self._tapped = set(), set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._last_input = clock()
        self.frame = Canvas()
        self.error = None

    # -- input from the browser ---------------------------------------------------

    def key(self, key, down):
        with self._lock:
            self._last_input = self.clock()
            if down:
                self._held.add(key)
                self._tapped.add(key)
            else:
                self._held.discard(key)
            if down and key == "space" and self.game.over:
                self.game = GAMES[self.name](random.Random())

    # -- the loop -----------------------------------------------------------------

    def _draw(self):
        c = Canvas()
        self.game.draw(c)
        if self.game.over:
            c.rect(0, 4, WIDTH, HEIGHT - 4, 0)
            c.text_centered(
                5,
                "GAME OVER" if self.name != "breakout" or self.game.bricks else "CLEARED",
                LED["white"],
                big=False,
            )
            score = f"SCORE {self.game.score}"
            c.text(
                (WIDTH - font.text_width(font.SMALL, score)) // 2,
                11,
                score,
                LED["amber"],
                big=False,
            )
        return c

    def _push(self, frame):
        px = themes.frames([frame.px], self.theme)[0]
        self.device.push(APP, {"draw": [{"db": [0, 0, WIDTH, HEIGHT, list(px)]}]})

    def run(self):
        try:
            hold.hold(hold.LIVE_SECONDS)
            self._push(self._draw())
            self.device.switch_custom(APP)
            while not self._stop.is_set():
                started = self.clock()
                with self._lock:
                    pressed = self._held | self._tapped
                    self._tapped = set()
                    self.game.step(pressed)
                    self.frame = self._draw()
                self._push(self.frame)
                hold.hold(hold.LIVE_SECONDS)
                if self.clock() - self._last_input > IDLE_STOP:
                    break
                self._stop.wait(max(0, FRAME_MS / 1000 - (self.clock() - started)))
        except DeviceError as exc:
            self.error = str(exc)
        finally:
            self._finish()

    def _finish(self):
        self._stop.set()  # also when the loop ended by itself (idle, or the clock went away)
        with contextlib.suppress(DeviceError):  # a clock that is gone has nothing to tidy
            self.device.remove(APP)
        hold.release()

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self):
        self._stop.set()

    @property
    def running(self):
        return not self._stop.is_set() and self.error is None

    def snapshot(self):
        """What the browser mirrors."""
        with self._lock:
            return {
                "game": self.name,
                "px": themes.frames([self.frame.px], self.theme)[0],
                "score": self.game.score,
                "over": self.game.over,
                "running": self.running,
                "error": self.error,
            }
