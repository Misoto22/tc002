"""Output: change-only pushes and quiet retries while the clock is away."""

from tc002.clock.device import DeviceError
from tc002.render.anim import Animation
from tc002.render.canvas import Canvas
from tc002.runtime.output import Output


class FlakyDevice:
    def __init__(self):
        self.up, self.pushes = True, []

    def push(self, app, payload):
        if not self.up:
            raise DeviceError("timed out")
        self.pushes.append(app)


def anim(key):
    return Animation.still(Canvas(), key=key)


def test_unchanged_key_is_not_pushed_twice():
    dev = FlakyDevice()
    out = Output(dev)
    out.show("claude", anim("idle"))
    out.show("claude", anim("idle"))
    out.show("claude", anim("busy"))
    assert dev.pushes == ["claude", "claude"]


def test_outage_logs_once_and_recovery_repushes(capsys):
    dev = FlakyDevice()
    out = Output(dev)
    dev.up = False
    for _ in range(5):
        out.show("sys", anim("same"))
    assert capsys.readouterr().err.count("retrying quietly") == 1
    dev.up = True
    out.show("sys", anim("same"))  # never delivered, so the same key must still go out
    assert dev.pushes == ["sys"]
    assert "reachable again" in capsys.readouterr().err


def test_shutdown_removes_each_screen_once_with_a_short_timeout(monkeypatch):
    """With the clock off, the default 2 x 5 s per removal outlasted launchd's stop."""
    import threading
    from types import SimpleNamespace

    from tc002.runtime import watcher

    handlers = {}

    class Screen:
        APP, TICK = "sys", 60

        def sample(self):
            handlers["term"]()  # launchd's SIGTERM arrives while the service runs
            raise OSError("clock off")

        def render(self, state):
            return anim(state)

    class OffClock:
        def __init__(self):
            self.removes = []

        def push(self, app, payload, **request):
            raise DeviceError("timed out")

        def remove(self, app, **request):
            self.removes.append((app, request))
            raise DeviceError("timed out")

    class Idle:
        def __init__(self, *args, **kwargs):
            self.dark = lambda: False

        def run(self, stop):
            stop.wait()

    monkeypatch.setattr(watcher, "build", lambda name, settings: Screen())
    monkeypatch.setattr(watcher.night, "Watch", Idle)
    monkeypatch.setattr(watcher, "Rotation", Idle)
    monkeypatch.setattr(
        watcher.signal, "signal", lambda sig, fn: handlers.__setitem__("term", lambda: fn())
    )
    settings = SimpleNamespace(
        led_theme=None, screens=["sys", "sys2"], schedule=[], alert_takeover=True, source="x"
    )
    dev = OffClock()
    done = threading.Thread(target=watcher.watch, args=(dev, settings))
    done.start()
    done.join(timeout=10)
    assert not done.is_alive()
    assert dev.removes == [
        ("sys", {"timeout": watcher.REMOVE_TIMEOUT, "attempts": 1}),
        ("sys", {"timeout": watcher.REMOVE_TIMEOUT, "attempts": 1}),
    ]
