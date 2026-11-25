"""`tc002 watch`: one thread per screen plus the rotation driver, until Ctrl-C or SIGTERM."""

import signal
import subprocess
import threading
import time

from ..clock import tz
from ..screens import build, stale
from . import night
from .freshness import Freshness
from .output import Output, log
from .rotation import Attention, Rotation

JOIN_WAIT = 5  # seconds the screen threads get, together, to finish after a stop
REMOVE_TIMEOUT = 1  # per screen removal on the way out


def _show_stale(out, screen, freshness):
    """After a failed sample: the last picture with its age, then NO DATA (screens/stale.py)."""
    state, age = freshness.last(screen.APP)
    if age is not None and age < stale.STALE_AFTER:
        return  # a blip: leave the last good picture up
    if state is not None and age < stale.NO_DATA_AFTER:
        out.show(screen.APP, stale.mark(screen.render(state), age))
    else:
        out.show(screen.APP, stale.no_data(screen.APP, age))


def _tick(out, screen, attention, freshness):
    """One sample + render of `screen`; an expected probe failure shows the stale picture."""
    try:
        state = screen.sample()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        # a failed probe must not kill a long-running watcher
        log(f"[{screen.APP}] sample failed: {exc}")
        freshness.failed(screen.APP, exc)
        _show_stale(out, screen, freshness)
        return
    anim = screen.render(state)
    freshness.ok(screen.APP, state)
    out.show(screen.APP, anim)
    if hasattr(state, "alert"):
        current = attention.get()
        if state.alert:
            attention.set(screen.APP)
        elif current == screen.APP:
            attention.set(None)


def screen_loop(out, screen, stop, attention, once=False, freshness=None):
    """Sample + render `screen` every screen.TICK seconds until `stop` is set."""
    freshness = freshness or Freshness()
    while not stop.is_set():
        try:
            _tick(out, screen, attention, freshness)
        except Exception as exc:  # noqa: BLE001 — the thread must outlive any bug
            # a screen bug (a None in an API reply, a division by zero) must not kill the
            # thread silently and leave the clock frozen on its last picture
            log(f"[{screen.APP}] failed: {type(exc).__name__}: {exc}")
            freshness.failed(screen.APP, exc)
            try:
                _show_stale(out, screen, freshness)
            except Exception as again:  # noqa: BLE001
                log(f"[{screen.APP}] stale picture failed: {type(again).__name__}: {again}")
        if once:
            return
        stop.wait(screen.TICK)


def watch(device, settings, preview_dir=None, once=False):
    """Run the configured screens (and, on a real clock, the rotation driver)."""
    darkness = night.Watch(device, settings, log=log) if device is not None and not once else None
    dark = darkness.dark if darkness else (lambda: False)
    out = Output(device, preview_dir, theme=settings.led_theme, paused=dark)
    screens = [build(name, settings) for name in settings.screens]
    stop = threading.Event()
    attention = Attention()
    freshness = Freshness()  # shared: one status file for every screen
    if not once:
        signal.signal(signal.SIGTERM, lambda *_: stop.set())  # launchd stop
    threads = [
        threading.Thread(
            target=screen_loop, args=(out, s, stop, attention, once, freshness), daemon=True
        )
        for s in screens
    ]
    if device is not None and not once:
        rotation = Rotation(
            device, settings.schedule, attention, settings.alert_takeover, dark=dark
        )
        threads.append(threading.Thread(target=rotation.run, args=(stop,), daemon=True))
    for t in threads:
        t.start()
    log(f"watching {', '.join(s.APP for s in screens)} (config: {settings.source})")
    follow = None
    if (
        device is not None
        and not once
        and getattr(settings, "display", {}).get("timezone") == "auto"
    ):
        follow = tz.Follow(device, log=log)  # the clock moves when this Mac does
    try:
        while any(t.is_alive() for t in threads) and not stop.is_set():
            if follow:
                follow.tick()
            stop.wait(0.5)
    except KeyboardInterrupt:
        pass
    stop.set()
    deadline = time.monotonic() + JOIN_WAIT  # one budget for all threads, not 5 s each
    for t in threads:
        t.join(timeout=max(0, deadline - time.monotonic()))
    if not once:
        # one quick try each: with the clock off, 2 x 5 s per screen would outlast
        # launchd's stop (host/launchd.py) and fail `tc002 uninstall`
        for s in screens:
            out.remove(s.APP, timeout=REMOVE_TIMEOUT, attempts=1)
        log("stopped; screens removed from the clock")
