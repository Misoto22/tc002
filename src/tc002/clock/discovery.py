"""Finding a TC002 on the LAN.

Discovery asks every address of this Mac's /24 for the firmware's /getBase, many at
once with a short timeout; only replies that look like a TC002 count. Nothing is sent
beyond the local subnet.
"""

import socket
from concurrent.futures import ThreadPoolExecutor

from . import provision
from .device import MIN_FIRMWARE, Device, DeviceError, firmware

PROBE_TIMEOUT = 0.8
WORKERS = 64


def local_subnet():
    """ "192.168.4" for this Mac's primary IPv4 address, or None when offline.

    Connecting a UDP socket sends nothing; it only makes the OS pick the route.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))  # TEST-NET-1: never routed anywhere real
            address = s.getsockname()[0]
        except OSError:
            return None
    return address.rsplit(".", 1)[0] if not address.startswith("127.") else None


def probe(host, timeout=PROBE_TIMEOUT):
    """The clock's /getBase reply when `host` is a TC002, else None."""
    try:
        base = Device(host, timeout=timeout).base_info()
    except DeviceError:
        return None
    if not isinstance(base, dict) or not ({"appVer", "devSn"} & set(base)):
        return None
    return {
        "host": host,
        "appVer": base.get("appVer"),
        "name": base.get("devName") or "TC002",
        "supported": firmware(base.get("appVer")) >= MIN_FIRMWARE,
    }


def discover(subnet=None, timeout=PROBE_TIMEOUT, listen=provision.listen):
    """Clocks on this network: those heard announcing themselves (quick, exact), else a
    sweep of this Mac's /24 (for networks that drop broadcasts)."""
    heard = [c for c in (probe(a["host"], timeout) for a in listen()) if c]
    subnet = subnet or local_subnet()
    if heard:
        return {"subnet": f"{subnet}.0/24" if subnet else None, "clocks": heard, "how": "broadcast"}
    if subnet is None:
        return {"subnet": None, "clocks": [], "how": "none"}
    hosts = [f"{subnet}.{i}" for i in range(1, 255)]
    with ThreadPoolExecutor(WORKERS) as pool:
        found = [c for c in pool.map(lambda h: probe(h, timeout), hosts) if c]
    return {"subnet": f"{subnet}.0/24", "clocks": found, "how": "sweep"}
