"""`tc002 watch`: one thread per screen plus the rotation driver, until Ctrl-C or SIGTERM."""

import signal
import subprocess
import threading

from ..screens import build, stale
from .freshness import Freshness
from .output import Output, log
from .rotation import Attention, Rotation


def _show_stale(out, screen, freshness):
    """After a failed sample: the last picture with its age, then NO DATA (screens/stale.py)."""
    state, age = freshness.last(screen.APP)
    if age is not None and age < stale.STALE_AFTER:
        return  # a blip: leave the last good picture up
    if state is not None and age < stale.NO_DATA_AFTER:
        out.show(screen.APP, stale.mark(screen.render(state), age))
    else:
        out.show(screen.APP, stale.no_data(screen.APP, age))


def screen_loop(out, screen, stop, attention, once=False, freshness=None):
    """Sample + render `screen` every screen.TICK seconds until `stop` is set."""
    freshness = freshness or Freshness()
    while not stop.is_set():
        try:
            state = screen.sample()
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            # a failed probe must not kill a long-running watcher
            log(f"[{screen.APP}] sample failed: {exc}")
            freshness.failed(screen.APP, exc)
            _show_stale(out, screen, freshness)
        else:
            freshness.ok(screen.APP, state)
            out.show(screen.APP, screen.render(state))
            if hasattr(state, "alert"):
                current = attention.get()
                if state.alert:
                    attention.set(screen.APP)
                elif current == screen.APP:
                    attention.set(None)
        if once:
            return
        stop.wait(screen.TICK)


def watch(device, settings, preview_dir=None, once=False):
    """Run the configured screens (and, on a real clock, the rotation driver)."""
    out = Output(device, preview_dir, theme=settings.led_theme)
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
        rotation = Rotation(device, settings.schedule, attention, settings.alert_takeover)
        threads.append(threading.Thread(target=rotation.run, args=(stop,), daemon=True))
    for t in threads:
        t.start()
    log(f"watching {', '.join(s.APP for s in screens)} (config: {settings.source})")
    try:
        while any(t.is_alive() for t in threads) and not stop.is_set():
            stop.wait(0.5)
    except KeyboardInterrupt:
        pass
    stop.set()
    for t in threads:
        t.join(timeout=5)
    if not once:
        for s in screens:
            out.remove(s.APP)
        log("stopped; screens removed from the clock")
