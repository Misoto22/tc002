"""Use cases for setting tc002 up: remember a clock, find one on the LAN, write a first
tc002.toml, and hand a new clock this Mac's Wi-Fi."""

from pathlib import Path

from .. import config
from ..clock import discovery, provision
from ..config import presets, writer
from .errors import AppError, CommandFailed, InvalidRequest, InvalidSettings


class Setup:
    def setup_local(self, host, config_path=None):
        """`tc002 setup`: remember the clock's address and which tc002.toml to use, then
        check that file now rather than in the service."""
        if config_path:
            config_path = str(Path(config_path).expanduser().resolve())
        saved = config.save_local(host=host, config=config_path)
        config.load()
        self.host, self.config_path = host, config.path()
        return {"file": str(config.LOCAL_FILE), "saved": saved}

    def discover(self):
        """Clocks on this network (announced, else found by sweeping this Mac's /24)."""
        return discovery.discover()

    def first_run(self, host, preset=None, timezone=None, weather=None):
        """Remember `host` and give it its first settings: a new ~/.config/tc002/tc002.toml
        from `preset` when none is set yet, plus the time zone and weather city if given,
        then push them to the clock."""
        host = str(host or "").strip()
        if not host or len(host) > 253 or any(c.isspace() for c in host):
            raise InvalidRequest("Invalid address", "Give the clock's IP address or host name.")
        if discovery.probe(host, timeout=3) is None:
            raise InvalidRequest("No clock there", f"no TC002 answered at {host}")
        path = config.path()
        if path is None:
            path = config.STATE_DIR / "tc002.toml"
            data = config.to_data(config.Settings())
            if preset:
                data = presets.apply(data, preset)
        else:
            data = config.to_data(config.load(path))
        if timezone:
            data["display"] = {**data["display"], "timezone": timezone}
        if weather:
            city = {k: str(weather[k]) for k in ("city", "lat", "lon") if weather.get(k)}
            data["apps"] = {**data["apps"], "weather": {**data["apps"].get("weather", {}), **city}}
        try:
            settings = config.parse(data, str(path))
        except config.ConfigError as exc:  # e.g. a bad time zone
            raise InvalidSettings("Invalid settings", str(exc)) from None
        path.parent.mkdir(parents=True, exist_ok=True)
        with writer.WRITE_LOCK:
            writer.save(settings, path)
        config.save_local(host=host, config=str(path))
        self.host, self.config_path = host, config.path()
        try:  # the clock should look like its new settings straight away
            changes = self.apply()
        except AppError as exc:
            changes = [f"not applied yet: {exc.detail}"]
        return {"host": host, "config": str(path), "changes": changes}

    # -- Wi-Fi for a new clock ------------------------------------------------------

    def wifi_status(self):
        """Whether this Mac can see a clock on its setup hotspot right now."""
        return {
            "onHotspot": discovery.probe(provision.HOTSPOT_HOST, timeout=1) is not None,
            "hotspot": provision.HOTSPOT_SSID,
            "hotspotPassword": provision.HOTSPOT_PASSWORD,
        }

    def wifi_join_hotspot(self):
        problem = provision.join(provision.HOTSPOT_SSID, provision.HOTSPOT_PASSWORD)
        if problem:
            raise CommandFailed("Request failed", problem)
        return {"joined": provision.HOTSPOT_SSID}

    def wifi_send(self, ssid, password):
        """Pass the home Wi-Fi to the clock. The password goes to the clock only."""
        provision.send_wifi(str(ssid or ""), str(password or ""))
        return {"sent": True}

    def wifi_rejoin(self, ssid):
        """Put this Mac back on its own network (macOS uses the password it saved)."""
        ssid = str(ssid or "")
        if not ssid:
            raise InvalidRequest("Invalid settings", "Name the network to go back to.")
        problem = provision.join(ssid)
        return {"rejoined": problem is None, "detail": problem}
