"""Decides what the clock shows: a playlist of slots, interrupted by alerts.

The device's own carousel is switched off by `tc002 layout apply`; this driver takes
its place, stepping through custom screens (`/api/switchDiyApp`) and the built-in apps
you kept (`/switchApp`). When a screen raises an alert (Claude DONE/WAIT) it jumps
there at once and holds until the alert clears.
"""

import threading
import time

from .. import builtins
from ..device import DeviceError
from .output import Quiet, log

POLL = 0.5


class Attention:
    """Thread-safe 'which screen needs to be seen now', set by screen loops."""

    def __init__(self):
        self._lock = threading.Lock()
        self._app = None

    def set(self, app):
        with self._lock:
            self._app = app

    def get(self):
        with self._lock:
            return self._app


class Playlist:
    def __init__(self, device, slots, attention, takeover=True, clock=time.monotonic):
        self.device, self.slots, self.attention = device, list(slots), attention
        self.takeover, self.clock = takeover, clock
        self._quiet = Quiet()
        self.showing = None  # label of what was last switched to

    def _switch(self, label, action):
        try:
            action()
        except DeviceError as exc:
            self._quiet.failed(f"switch {label}", exc)
            return False
        self._quiet.ok(f"switch {label}")
        self.showing = label
        return True

    def _show_slot(self, slot):
        if slot.screen:
            return self._switch(slot.label, lambda: self.device.switch_custom(slot.screen))
        app = builtins.lookup(slot.builtin)
        return self._switch(slot.label, lambda: self.device.switch_builtin(app.category, app.index))

    def step(self, state):
        """One scheduling decision. `state` is (slot index, slot started at)."""
        index, started = state
        urgent = self.attention.get() if self.takeover else None
        if urgent:
            if self.showing != urgent:
                self._switch(urgent, lambda: self.device.switch_custom(urgent))
            return index, None  # restart the interrupted slot's clock afterwards
        if not self.slots:
            return index, started
        slot = self.slots[index % len(self.slots)]
        now = self.clock()
        if started is None or self.showing != slot.label:
            if self._show_slot(slot):
                return index, now
            return index, None
        if now - started >= slot.seconds:
            nxt = (index + 1) % len(self.slots)
            self._show_slot(self.slots[nxt])
            return nxt, now
        return index, started

    def run(self, stop):
        if self.slots:
            log("playlist: " + " -> ".join(f"{s.label} {s.seconds:g}s" for s in self.slots))
        state = (0, None)
        while not stop.is_set():
            state = self.step(state)
            stop.wait(POLL)
