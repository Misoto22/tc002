"""JSON API behind `tc002 ui`: read everything, change tc002.toml, act on the clock.

Every change goes through tc002.toml first (validated by `config.parse`), then
`sync.apply` pushes it to the clock and the background service is restarted so it
reloads the playlist. Credentials stored on the clock are never read out: only their
presence is reported.
"""

import threading
import time

from .. import builtins, config, config_writer, device_settings, sync
from ..device import CATEGORY_ENDPOINTS, Device, DeviceError
from ..integrations import claude_hooks, executable, launchd
from ..render import font, mockup
from ..runtime import events, hold
from ..screens import SCREENS, message
from ..screens.examples import examples
from . import cities

SECRET_KEYS = {"token", "password", "username", "url", "tokens"}


class ApiError(Exception):
    """Becomes an RFC 9457 problem response."""

    def __init__(self, status, title, detail, errors=None):
        super().__init__(detail)
        self.status, self.title, self.detail, self.errors = status, title, detail, errors


class Api:
    def __init__(self, host, config_path, state_dir=None):
        self.host, self.config_path = host, config_path
        self.state_dir = state_dir or config.STATE_DIR

    # -- helpers ------------------------------------------------------------------

    def _device(self):
        if not self.host:
            raise ApiError(409, "No clock configured", "Run `tc002 setup --host <IP>` first.")
        return Device(self.host, timeout=4)

    def _settings(self):
        return config.load(self.config_path)

    # -- reads --------------------------------------------------------------------

    def state(self):
        settings = self._settings()
        return {
            "config": {
                "path": str(self.config_path) if self.config_path else None,
                "data": config.to_data(settings),
            },
            "clock": self._clock_state(settings),
            "integrations": self._integrations(),
            "catalogue": [
                {"key": k, "category": b.category, "index": b.index}
                for k, b in builtins.CATALOGUE.items()
            ],
            "screens": sorted(SCREENS),
            "schema": device_settings.schema(),
            "colors": message.COLORS,
            "alertKinds": list(message.ICONS),
        }

    def _clock_state(self, settings):
        if not self.host:
            return {"online": False, "error": "no clock configured"}
        dev = self._device()
        try:
            base, cfg = dev.info()["base"], dev.config()
            categories = {c: dev.category_config(c) for c in CATEGORY_ENDPOINTS}
            apps = dev.apps()
        except DeviceError as exc:
            return {"online": False, "host": self.host, "error": str(exc)}
        enabled = {}
        for category, (_, _, infos_key, _) in CATEGORY_ENDPOINTS.items():
            for key, info in categories[category].get(infos_key, {}).items():
                if key in builtins.CATALOGUE:
                    enabled[key] = {
                        "enabled": bool(info.get("enable")),
                        "credentials": any(info.get(s) for s in SECRET_KEYS & set(info)),
                    }
        tools = categories["tools"].get("toolsInfos", {})
        app_settings = {
            app: {k: tools.get(app, {}).get(k) for k in rules}
            for app, rules in device_settings.APPS.items()
        }
        return {
            "online": True,
            "host": self.host,
            "base": base,
            "settings": cfg,
            "builtins": enabled,
            "apps": app_settings,
            "customApps": apps,
            "drift": _drift(settings, cfg, app_settings, enabled),
        }

    def _integrations(self):
        try:
            hooks = claude_hooks.status(executable())
        except RuntimeError as exc:
            hooks = {"error": str(exc)}
        kind, at = events.latest()
        return {
            "service": launchd.status(),
            "hooks": hooks,
            "lastEvent": {"kind": kind, "secondsAgo": round(time.time() - at)} if kind else None,
        }

    def font(self):
        """The pixel fonts, so the browser's LED simulator draws exactly what the clock would."""
        return {"big": font.BIG, "small": font.SMALL}

    def cities(self, query):
        return cities.search(query.get("q", ""), query.get("lang", "en"))

    def preview(self, name, query):
        """LED mock-up GIF bytes for an example screen or a message draft."""
        if name == "text":
            anim = message.text_animation(
                query.get("text", "TEXT")[:60], query.get("color", "white")
            )[0]
        elif name == "alert":
            anim = message.alert_animation(
                query.get("text", "DONE")[:12], query.get("kind", "done"), query.get("color")
            )
        else:
            anims = examples()
            if name not in anims:
                raise ApiError(404, "Unknown preview", f"No preview named {name!r}.")
            anim = anims[name]
        return mockup.led_gif(anim)

    # -- writes -------------------------------------------------------------------

    def save_config(self, data):
        """Validate, write tc002.toml, push it to the clock, reload the service."""
        if not self.config_path:
            raise ApiError(409, "No tc002.toml", "Run `tc002 setup --config <path>` first.")
        try:
            settings = config.parse(data, str(self.config_path))
        except config.ConfigError as exc:
            problems = str(exc).split(": ", 1)[-1].split("; ")
            raise ApiError(
                422,
                "Invalid settings",
                "tc002.toml was not changed.",
                [{"field": "config", "message": p} for p in problems],
            ) from None
        config_writer.save(settings, self.config_path)
        result = {"saved": str(self.config_path), "changes": [], "applied": False}
        if self.host:
            try:
                result["changes"] = sync.apply(self._device(), settings, self.state_dir)
                result["applied"] = True
            except DeviceError as exc:
                result["error"] = f"saved, but the clock is unreachable: {exc}"
        result["serviceRestarted"] = launchd.restart()
        return result

    def live(self, body):
        """Put a draft on the clock without saving it, and keep the playlist off the screen."""
        data, focus = body.get("data"), body.get("focus") or {}
        try:
            settings = config.parse(data or {}, "draft")
        except config.ConfigError as exc:
            raise ApiError(422, "Invalid settings", str(exc).split(": ", 1)[-1]) from None
        dev = self._device()
        hold.hold(120)
        changes = sync.apply(dev, settings, self.state_dir)
        if focus:
            self.show(focus)
        return {"changes": changes, "heldFor": 120}

    def live_stop(self, body):
        """Put the saved tc002.toml back on the clock and hand the screen back to the playlist."""
        hold.release()
        if not self.host:
            return {"changes": []}
        return {"changes": sync.apply(self._device(), self._settings(), self.state_dir)}

    def show(self, body):
        dev = self._device()
        if body.get("screen"):
            dev.switch_custom(body["screen"])
        elif body.get("builtin"):
            app = builtins.lookup(body["builtin"])
            dev.switch_builtin(app.category, app.index)
        else:
            raise ApiError(422, "Nothing to show", "Send `screen` or `builtin`.")
        return {"ok": True}

    def send_message(self, body):
        """Text or alert, played in the background so the request returns at once."""
        dev = self._device()
        text = str(body.get("text", "")).strip()
        if not text:
            raise ApiError(422, "Empty message", "Type something to send.")
        if body.get("type") == "alert":
            anim = message.alert_animation(text, body.get("kind", "done"), body.get("color"))
            segments, app = [anim], "alert"
        else:
            segments, app = message.text_animation(text, body.get("color", "white")), "msg"
        threading.Thread(target=_play, args=(dev, app, segments), daemon=True).start()
        return {"ok": True, "app": app, "seconds": round(sum(s.duration_s() for s in segments))}


def _play(dev, app, segments, hold=10):
    try:
        for seg in segments:
            dev.push(app, seg.payload())
            dev.switch_custom(app)
            time.sleep(max(seg.duration_s(), hold if len(segments) == 1 else 0))
        dev.remove(app)
    except DeviceError:
        pass  # best effort: the UI already reported the request as accepted


def _drift(settings, cfg, app_settings, enabled):
    """Where the clock differs from tc002.toml (e.g. changed on the device itself)."""
    drift = []
    for key, value in settings.display.items():
        current = cfg.get(key)
        if isinstance(value, dict) and isinstance(current, dict):
            if any(current.get(k) != v for k, v in value.items()):
                drift.append(f"display.{key}")
        elif current != value:
            drift.append(f"display.{key}")
    for app, fields in settings.apps.items():
        for key, value in fields.items():
            current = app_settings.get(app, {}).get(key)
            if isinstance(value, dict):  # e.g. weather.displayInfo may list only some flags
                same = isinstance(current, dict) and all(
                    current.get(k) == v for k, v in value.items()
                )
            else:
                same = current == value
            if not same:
                drift.append(f"apps.{app}.{key}")
    for key, state in enabled.items():
        if state["enabled"] != (key in settings.keep_builtins):
            drift.append(f"builtin.{key}")
    if settings.playlist and cfg.get("carouselSpeed"):
        drift.append("display.carouselSpeed")
    return drift
