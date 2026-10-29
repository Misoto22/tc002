"""Output: change-only pushes and quiet retries while the clock is away."""

from tc002.device import DeviceError
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
