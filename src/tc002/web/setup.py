"""First run from the UI: find the clock on the LAN, remember it, start a tc002.toml.

Discovery asks every address of this Mac's /24 for the firmware's /getBase, many at
once with a short timeout; only replies that look like a TC002 count. Nothing is sent
beyond the local subnet.
"""

import socket
from concurrent.futures import ThreadPoolExecutor

from .. import config, config_writer, presets
from ..device import Device, DeviceError

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
    return {"host": host, "appVer": base.get("appVer"), "name": base.get("devName") or "TC002"}


def discover(subnet=None, timeout=PROBE_TIMEOUT):
    subnet = subnet or local_subnet()
    if subnet is None:
        return {"subnet": None, "clocks": []}
    hosts = [f"{subnet}.{i}" for i in range(1, 255)]
    with ThreadPoolExecutor(WORKERS) as pool:
        found = [c for c in pool.map(lambda h: probe(h, timeout), hosts) if c]
    return {"subnet": f"{subnet}.0/24", "clocks": found}


def setup(host, preset=None):
    """Remember `host`; create ~/.config/tc002/tc002.toml when no tc002.toml is set yet."""
    if probe(host, timeout=3) is None:
        raise ValueError(f"no TC002 answered at {host}")
    path = config.path()
    if path is None:
        path = config.STATE_DIR / "tc002.toml"
        data = config.to_data(config.Settings())
        if preset:
            data = presets.apply(data, preset)
        path.parent.mkdir(parents=True, exist_ok=True)
        config_writer.save(config.parse(data, str(path)), path)
    config.save_local(host=host, config=str(path))
    return {"host": host, "config": str(path)}
