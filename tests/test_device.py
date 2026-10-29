"""Device client against a real local HTTP server that mimics the clock."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import ClassVar

import pytest

from tc002.device import Device, DeviceError


class FakeClock(BaseHTTPRequestHandler):
    apps: ClassVar[dict] = {}
    reply_code = 200

    def _reply(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Connection", "close")  # the real clock sends no Content-Length
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/api/customList":
            self._reply({"apps": list(self.apps), "count": len(self.apps)})
        elif self.path == "/getBase":
            self._reply({"ip": "127.0.0.1", "appVer": "1.1.3"})
        elif self.path == "/getConfig":
            self._reply({"timezone": "UTC+8"})
        else:
            self.send_error(404)

    def do_POST(self):
        name = self.path.split("name=", 1)[1]
        frame = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if frame:
            self.apps[name] = frame
        else:
            self.apps.pop(name, None)
        self._reply({"code": self.reply_code, "message": "ok"})

    def log_message(self, *args):
        pass


@pytest.fixture
def clock():
    FakeClock.apps, FakeClock.reply_code = {}, 200
    server = HTTPServer(("127.0.0.1", 0), FakeClock)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{server.server_port}"
    server.shutdown()


def test_push_list_remove_round_trip(clock):
    dev = Device(clock)
    dev.push("claude", {"duration": 5, "draw": []})
    assert dev.apps() == ["claude"]
    dev.remove("claude")
    assert dev.apps() == []


def test_info_combines_base_and_config(clock):
    info = Device(clock).info()
    assert info["base"]["appVer"] == "1.1.3"
    assert info["config"]["timezone"] == "UTC+8"


def test_rejected_frame_raises(clock):
    FakeClock.reply_code = 500
    with pytest.raises(DeviceError, match="rejected"):
        Device(clock).push("x", {"draw": []})


def test_unreachable_clock_raises_device_error():
    with pytest.raises(DeviceError):
        Device("127.0.0.1:9", timeout=0.5).apps()


def test_http_proxy_env_is_ignored(clock, monkeypatch):
    # Regression: a local Clash proxy in HTTP_PROXY made every request to the LAN hang.
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "")
    Device(clock, timeout=2).push("msg", {"draw": []})
    assert FakeClock.apps
