"""Where animations go: the clock, or LED mock-up GIFs on disk (`--preview`)."""

import sys
import time
from pathlib import Path

from ..device import DeviceError
from ..render import mockup

REFRESH = 60  # re-push an unchanged animation this often so a rebooted clock gets it back


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", file=sys.stderr, flush=True)


class Quiet:
    """Logs the first failure of a stream and its recovery, not every retry in between."""

    def __init__(self):
        self._down = set()

    def failed(self, name, exc):
        if name not in self._down:
            log(f"[{name}] failed, retrying quietly: {exc}")
            self._down.add(name)

    def ok(self, name):
        if name in self._down:
            self._down.discard(name)
            log(f"[{name}] clock reachable again")


class Output:
    """Pushes animations, skipping ones whose key matches the last successful push."""

    def __init__(self, device, preview_dir=None, duration=10):
        self.device = device
        self.preview_dir = Path(preview_dir) if preview_dir else None
        self.duration = duration
        self._last = {}
        self._quiet = Quiet()

    def show(self, app, anim):
        if self.device is None:
            path = self.preview_dir / f"tc002-{app}.gif"
            path.write_bytes(mockup.led_gif(anim))
            print(f"[{app}] {len(anim.frames)} frames -> {path}")
            print(anim.frames[0].ansi())
            return
        now = time.monotonic()
        last = self._last.get(app)
        if anim.key is not None and last and last[0] == anim.key and now - last[1] < REFRESH:
            return
        try:
            self.device.push(app, anim.payload(self.duration))
        except DeviceError as exc:
            self._quiet.failed(app, exc)
            return
        self._last[app] = (anim.key, now)
        self._quiet.ok(app)

    def remove(self, app):
        if self.device is None:
            return
        try:
            self.device.remove(app)
        except DeviceError as exc:
            log(f"[{app}] remove failed: {exc}")
