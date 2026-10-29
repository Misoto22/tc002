"""Putting a new clock on Wi-Fi and hearing clocks announce themselves."""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from tc002 import provision


def test_wifi_details_are_checked_before_sending():
    assert provision.check_wifi("Home", "longenough") == []
    assert provision.check_wifi("", "x") and provision.check_wifi("Home", "short")
    assert provision.check_wifi("x" * 33, "") and provision.check_wifi("Open", "") == []


def _hotspot(replies):
    """A fake clock hotspot: first answers with a captive-portal redirect, then accepts."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(
                (self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            )
            status, body, location = replies.pop(0)
            self.send_response(status)
            if location:
                self.send_header("Location", location)
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    threading.Thread(target=server.handle_request, daemon=True).start()
    return server, seen


def test_send_follows_the_redirect_and_keeps_the_post():
    server, seen = _hotspot([(301, {}, "/setWifiConfig?portal=1"), (200, {"code": 200}, None)])
    host = f"127.0.0.1:{server.server_port}"
    assert provision.send_wifi("Home", "longenough", host=host)
    assert [p for p, _ in seen] == ["/setWifiConfig", "/setWifiConfig?portal=1"]
    assert seen[-1][1] == {"ssid": "Home", "password": "longenough"}
    server.server_close()


def test_send_errors_never_carry_the_password():
    with pytest.raises(provision.ProvisionError) as err:
        provision.send_wifi("Home", "secretpass1", host="127.0.0.1:9")  # nothing listens
    assert "secretpass1" not in str(err.value)


def test_listen_hears_announcements_once_per_clock():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    done = []

    def run():
        done.append(provision.listen(1.0, port=port))

    t = threading.Thread(target=run)
    t.start()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for _ in range(3):
            s.sendto(b"Ulanzi TC002 b9c0:ccc4b277b9c0:B0D34I008U3670947:false", ("127.0.0.1", port))
        s.sendto(b"something else", ("127.0.0.1", port))
    t.join()
    assert done[0] == [{"host": "127.0.0.1", "mac": "ccc4b277b9c0", "serial": "B0D34I008U3670947"}]
