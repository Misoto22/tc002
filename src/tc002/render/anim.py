"""An animation: canvases plus per-frame delays, shipped to the clock as one looping GIF."""

from dataclasses import dataclass, field

from . import gif
from .canvas import HEIGHT, WIDTH, Canvas

# Firmware limits for a GIF image element (protocol reference, section 4.2).
MAX_FRAMES = 50
MAX_DATA_URI_BYTES = 60 * 1024


@dataclass
class Animation:
    frames: list[Canvas]
    delay_ms: int | list[int] = 100
    # Screens set this to their state; the output re-pushes only when it changes.
    key: object = field(default=None, compare=False)

    @classmethod
    def still(cls, canvas, key=None):
        return cls([canvas], 1000, key)

    def delays(self):
        if isinstance(self.delay_ms, list):
            return self.delay_ms
        return [self.delay_ms] * len(self.frames)

    def duration_s(self):
        return sum(self.delays()) / 1000

    def gif(self):
        return gif.encode([f.px for f in self.frames], WIDTH, HEIGHT, self.delays())

    def payload(self, duration=10):
        """Device payload: the clock loops the GIF on its own until replaced."""
        if len(self.frames) > MAX_FRAMES:
            raise ValueError(f"{len(self.frames)} frames; the clock plays at most {MAX_FRAMES}")
        uri = gif.data_uri(self.gif())
        if len(uri) > MAX_DATA_URI_BYTES:
            raise ValueError(f"GIF is {len(uri)} bytes as base64; limit {MAX_DATA_URI_BYTES}")
        return {"duration": duration, "image": [{"data": uri, "position": [0, 0]}]}
