"""The clock's time zone following this Mac's, summer time included.

`[display] timezone = "auto"` sends the clock this Mac's zone as a POSIX rule (for
Sydney "AEST-10AEDT,M10.1.0,M4.1.0/3") through the firmware's `timezoneEx` setting, an
undocumented field that firmware 2.0.4 honours (see docs/device-notes.md). A fixed
`UTC±N` cannot follow summer time; the rule can, and the clock works it out itself.

The rule is the footer of the zone's TZif file, which /etc/localtime points at. macOS
moves that link when the Mac changes time zone, so the background service checks it
every minute (`Follow`) and sends the new rule.
"""

import time
from pathlib import Path

from .device import DeviceError

LOCALTIME = Path("/etc/localtime")
CHECK_EVERY = 60  # seconds between looks at this Mac's zone


def mac_zone(path=LOCALTIME):
    """(name, POSIX rule) of this Mac's time zone; ValueError when it cannot be read."""
    real = Path(path).resolve()
    name = str(real).split("zoneinfo/", 1)[-1]
    try:
        data = real.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read {real}: {exc}") from None
    # a version 2+ TZif file ends with "\n<POSIX rule>\n"
    if not data.startswith(b"TZif") or not data.endswith(b"\n"):
        raise ValueError(f"{real} is not a TZif file with a POSIX footer")
    rule = data[:-1].rsplit(b"\n", 1)[-1].decode("ascii", "replace")
    if not rule or "\x00" in rule:
        raise ValueError(f"{real} has no POSIX footer")
    return name, rule


def wanted(current_ex, zone=None):
    """The clock's timezoneEx that follows `zone` (default: this Mac's), keeping other keys."""
    name, rule = zone or mac_zone()
    return {**(current_ex or {}), "location": name, "customPosixEnabled": True, "customPosix": rule}


class Follow:
    """Keeps the clock on this Mac's time zone while the service runs."""

    def __init__(self, device, log=print, clock=time.monotonic, zone=mac_zone):
        self.device, self.log, self.clock, self.zone = device, log, clock, zone
        self._next = 0.0
        self._sent = None  # the rule the clock was last given (None: check the clock)

    def tick(self):
        now = self.clock()
        if now < self._next:
            return
        self._next = now + CHECK_EVERY
        try:
            zone = self.zone()
            if zone[1] == self._sent:
                return
            time.tzset()  # this process's own local time (the night schedule) follows too
            ex = self.device.config().get("timezoneEx") or {}
            want = wanted(ex, zone)
            if ex != want:
                self.device.set_config(timezoneEx=want)
                self.log(f"time zone: clock now follows {zone[0]} ({zone[1]})")
            self._sent = zone[1]
        except (DeviceError, ValueError) as exc:
            self.log(f"time zone: will try again ({exc})")
