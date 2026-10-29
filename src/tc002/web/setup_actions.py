"""API actions for finding a clock and setting it up from scratch (first run, Wi-Fi).

Mixed into web.api.Api; see web/setup.py for discovery and provision.py for Wi-Fi."""

from .. import config, provision, sync
from ..device import DeviceError
from . import setup
from .errors import ApiError


class SetupActions:
    def discover(self, query):
        return setup.discover()

    def first_run(self, body):
        host = str(body.get("host") or "").strip()
        if not host or len(host) > 253 or any(c.isspace() for c in host):
            raise ApiError(422, "Invalid address", "Give the clock's IP address or host name.")
        try:
            done = setup.setup(host, body.get("preset"), body.get("timezone"), body.get("weather"))
        except config.ConfigError as exc:
            raise ApiError(422, "Invalid settings", str(exc)) from None
        except ValueError as exc:
            raise ApiError(422, "No clock there", str(exc)) from None
        self.host, self.config_path = done["host"], config.path()
        try:  # the clock should look like its new settings straight away
            changes = sync.apply(self._device(), done["settings"], self.state_dir)
        except DeviceError as exc:
            changes = [f"not applied yet: {exc}"]
        return {"host": done["host"], "config": done["config"], "changes": changes}

    def wifi_status(self, query=None):
        """Whether this Mac can see a clock on its setup hotspot right now."""
        return {
            "onHotspot": setup.probe(provision.HOTSPOT_HOST, timeout=1) is not None,
            "hotspot": provision.HOTSPOT_SSID,
            "hotspotPassword": provision.HOTSPOT_PASSWORD,
        }

    def wifi_join_hotspot(self, body):
        problem = provision.join(provision.HOTSPOT_SSID, provision.HOTSPOT_PASSWORD)
        if problem:
            raise ApiError(409, "Request failed", problem)
        return {"joined": provision.HOTSPOT_SSID}

    def wifi_send(self, body):
        """Pass the home Wi-Fi to the clock. The password goes to the clock only."""
        try:
            provision.send_wifi(str(body.get("ssid") or ""), str(body.get("password") or ""))
        except provision.ProvisionError as exc:
            raise ApiError(422, "Invalid settings", str(exc)) from None
        return {"sent": True}

    def wifi_rejoin(self, body):
        """Put this Mac back on its own network (macOS uses the password it saved)."""
        ssid = str(body.get("ssid") or "")
        if not ssid:
            raise ApiError(422, "Invalid settings", "Name the network to go back to.")
        problem = provision.join(ssid)
        return {"rejoined": problem is None, "detail": problem}
