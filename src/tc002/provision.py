"""Getting a clock onto Wi-Fi, and hearing which clocks are on the network.

A factory-fresh TC002 (or one that cannot reach its saved network) opens a hotspot,
HOTSPOT_SSID with a fixed password, and answers at HOTSPOT_HOST. POST /setWifiConfig
with {ssid, password} makes it join that network; it replies before it tries, so a
wrong password or a 5 GHz-only network shows only as the clock not appearing. Once on a
network every clock broadcasts "Ulanzi TC002 <mac tail>:<mac>:<serial>:<flag>" on UDP
BROADCAST_PORT about once a second. Sources: the protocol file (/setWifiConfig) and
community notes on a factory unit; see docs/device-notes.md.

The Wi-Fi password is passed through to the clock and nowhere else: not stored, not
logged, not part of any error message.
"""

import json
import re
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

HOTSPOT_SSID = "U-Clock"
HOTSPOT_PASSWORD = "12345678"  # the same on every unit: printed in the clock's own setup
HOTSPOT_HOST = "192.168.100.1"
BROADCAST_PORT = 55555
SSID_MAX_BYTES = 32  # 802.11
PASSWORD_LENGTHS = (8, 63)  # WPA2 passphrase; empty for an open network
TIMEOUT = 5
_ANNOUNCE = re.compile(rb"^Ulanzi TC002 [0-9a-f]+:([0-9a-f]{12}):([A-Za-z0-9]+):")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib would follow the hotspot's redirect as a GET and drop the body; send_wifi
    follows it itself, as a POST."""

    def redirect_request(self, *args, **kwargs):
        return None


# no proxy (the clock is on the LAN) and no automatic redirects
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


class ProvisionError(ValueError):
    """The Wi-Fi details were refused, or the clock could not be reached on its hotspot."""


def check_wifi(ssid, password):
    """Problems with Wi-Fi details before anything is sent (empty list when fine)."""
    problems = []
    if not ssid or len(ssid.encode()) > SSID_MAX_BYTES:
        problems.append(f"The network name must be 1 to {SSID_MAX_BYTES} bytes.")
    lo, hi = PASSWORD_LENGTHS
    if password and not lo <= len(password) <= hi:
        problems.append(f"A Wi-Fi password has {lo} to {hi} characters.")
    return problems


def send_wifi(ssid, password, host=HOTSPOT_HOST):
    """Tell a clock on its hotspot which network to join. Follows the captive-portal
    redirect the hotspot answers with, keeping the POST."""
    if problems := check_wifi(ssid, password):
        raise ProvisionError(" ".join(problems))
    body = json.dumps({"ssid": ssid, "password": password or ""}).encode()
    url = f"http://{host}/setWifiConfig"
    for _ in range(3):
        req = urllib.request.Request(
            url, data=body, method="POST", headers={"Content-Type": "application/json"}
        )
        try:
            with _DIRECT.open(req, timeout=TIMEOUT) as resp:
                reply = json.loads(resp.read() or b"{}")
            break
        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 307, 308) and exc.headers.get("Location"):
                url = urllib.parse.urljoin(url, exc.headers["Location"])
                continue
            raise ProvisionError(
                f"The clock refused the Wi-Fi details (HTTP {exc.code})."
            ) from None
        except urllib.error.URLError, OSError, ValueError:
            raise ProvisionError(
                f"No clock answered at {host}. Is this Mac on the {HOTSPOT_SSID} network?"
            ) from None
    else:
        raise ProvisionError("The clock kept redirecting the request.")
    if reply.get("code") not in (None, 200):
        raise ProvisionError(f"The clock refused the Wi-Fi details: {reply.get('message', '')}")
    return True


def listen(seconds=3.0, port=BROADCAST_PORT):
    """Clocks heard announcing themselves: [{"host", "mac", "serial"}], one per clock."""
    found = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):  # the background service may be listening too
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        try:
            s.bind(("", port))
        except OSError:
            return []
        end = time.monotonic() + seconds
        while (left := end - time.monotonic()) > 0:
            s.settimeout(left)
            try:
                data, (host, _) = s.recvfrom(512)
            except TimeoutError:
                break
            if m := _ANNOUNCE.match(data):
                found[m.group(1)] = {
                    "host": host,
                    "mac": m.group(1).decode(),
                    "serial": m.group(2).decode(),
                }
    return list(found.values())


# -- the Mac's own Wi-Fi (macOS) ------------------------------------------------------


def wifi_interface():
    """The Wi-Fi device name (e.g. en0), or None when there is none or this is not macOS."""
    try:
        out = subprocess.run(
            ["networksetup", "-listallhardwareports"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout
    except OSError, subprocess.SubprocessError:
        return None
    m = re.search(r"Hardware Port: Wi-Fi\nDevice: (\S+)", out)
    return m.group(1) if m else None


def join(ssid, password=None):
    """Join a Wi-Fi network; without a password macOS uses the one it has saved.

    Returns None on success, else what macOS said (it reports failures on stdout).
    """
    device = wifi_interface()
    if device is None:
        return "No Wi-Fi interface found on this Mac."
    cmd = ["networksetup", "-setairportnetwork", device, ssid]
    if password:
        cmd.append(password)
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"Could not change Wi-Fi: {type(exc).__name__}"
    said = (done.stdout + done.stderr).strip()
    # networksetup can exit 0 and still say it failed
    if done.returncode == 0 and not any(w in said for w in ("Error", "Could not", "Failed")):
        return None
    return said or "Could not join the network."
