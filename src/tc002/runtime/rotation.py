"""Decides what the clock shows: a rotation of slots, interrupted by alerts.

The device's own carousel is switched off by `tc002 layout apply`; this driver takes
its place, stepping through custom screens (`/api/switchDiyApp`) and the built-in apps
you kept (`/switchApp`). When a screen raises an alert (Claude DONE/WAIT) it jumps
there at once and holds until the alert clears. While the web UI's live preview holds
the screen (see hold.py) it switches nothing, and while the screen is meant to be dark
(night.py) it switches nothing either: any switch would light it.
"""

import threading
import time

from ..clock import builtins
from ..clock.device import DeviceError
from ..state import hold
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


class Rotation:
    def __init__(
        self,
        device,
        slots,
        attention,
        takeover=True,
        clock=time.monotonic,
        held=hold.active,
        dark=lambda: False,
    ):
        self.device, self.slots, self.attention = device, list(slots), attention
        self.takeover, self.clock, self.held, self.dark = takeover, clock, held, dark
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
        return self._switch(slot.label, lambda: _switch_builtin(self.device, app))

    def step(self, state):
        """One scheduling decision. `state` is (slot index, slot started at)."""
        index, started = state
        if self.dark():  # night: hands off, or the switch would light the screen
            self.showing = None  # show the current slot again in the morning
            return index, None
        if self.held():  # the UI is previewing something on the clock
            self.showing = None  # re-show the current slot once the hold ends
            return index, None
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
            log("rotation: " + " -> ".join(f"{s.label} {s.seconds:g}s" for s in self.slots))
        state = (0, None)
        while not stop.is_set():
            try:
                state = self.step(state)
            except Exception as exc:  # noqa: BLE001 — the thread must outlive any bug
                # e.g. a malformed reply: log it and keep rotating rather than die silently
                log(f"rotation step failed: {type(exc).__name__}: {exc}")
                self.showing = None
            stop.wait(POLL)


def _switch_builtin(device, app):
    """/switchApp, with a 404 explained: the firmware only switches to apps that are on,
    and some it hides altogether (builtins.HIDDEN_KEY)."""
    try:
        device.switch_builtin(app.category, app.index)
    except DeviceError as exc:
        if exc.status != 404:
            raise
        raise DeviceError(
            f"{exc} ({app.key} is off on the clock, or its firmware hides it: see `tc002 doctor`)",
            404,
        ) from exc
