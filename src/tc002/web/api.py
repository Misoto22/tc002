"""JSON API behind `tc002 ui`: read everything, change tc002.toml, act on the clock.

Every change goes through tc002.toml first (validated by `config.parse`), then
`sync.apply` pushes it to the clock and the background service is restarted so it
reloads the rotation. Credentials stored on the clock are never read out: only their
presence is reported.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from .. import builtins, config, config_writer, device_settings, presets, sync
from ..device import CATEGORY_ENDPOINTS, Device, DeviceError
from ..integrations import claude_hooks, executable, launchd, statusline
from ..render import font, mockup, themes
from ..render.canvas import HEIGHT, WIDTH
from ..render.palette import hex_palette
from ..runtime import freshness, hold
from ..screens import SCREENS, builtin_previews, message, stale
from ..screens import usage as usage_screen
from ..screens.examples import examples
from . import cities, host_actions, setup
from .agents import Agents

LIVE_SCREENS = {"claude", "usage"}  # cheap to sample: previewed with real data
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
        self.agents = Agents()

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
            "agents": self.agents.snapshot(),
            "freshness": freshness.read(),
            "staleAfter": {"age": stale.STALE_AFTER, "noData": stale.NO_DATA_AFTER},
            "catalogue": [
                {"key": k, "category": b.category, "index": b.index}
                for k, b in builtins.CATALOGUE.items()
            ],
            "screens": sorted(SCREENS),
            "schema": device_settings.schema(),
            "colors": message.COLORS,
            "alertKinds": list(message.ICONS),
            "messageMaxChars": message.MAX_CHARS,
            "limits": {"warn": usage_screen.WARN, "critical": usage_screen.CRITICAL},
            "slotSeconds": {"min": config.MIN_SLOT_SECONDS, "max": config.MAX_SLOT_SECONDS},
            "presets": presets.describe(),
            "ledThemes": themes.names(),
        }

    def _clock_state(self, settings):
        if not self.host:
            return {"online": False, "error": "no clock configured"}
        dev = self._device()
        # six independent reads: asked at once, the page waits for the slowest, not the sum
        calls = {"base": dev.base_info, "config": dev.config, "apps": dev.apps}
        calls |= {c: (lambda c=c: dev.category_config(c)) for c in CATEGORY_ENDPOINTS}
        try:
            with ThreadPoolExecutor(len(calls)) as pool:
                futures = {name: pool.submit(call) for name, call in calls.items()}
                got = {name: f.result() for name, f in futures.items()}
            base, cfg, apps = got["base"], got["config"], got["apps"]
            categories = {c: got[c] for c in CATEGORY_ENDPOINTS}
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
            exe = executable()
            hooks, wrapped = claude_hooks.status(exe), statusline.status(exe)
        except RuntimeError as exc:
            hooks, wrapped = {"error": str(exc)}, False
        return {"service": launchd.status(), "hooks": hooks, "statusline": wrapped}

    def agents_now(self, query=None):
        return self.agents.snapshot()

    def discover(self, query):
        return setup.discover()

    def first_run(self, body):
        host = str(body.get("host") or "").strip()
        if not host or len(host) > 253 or any(c.isspace() for c in host):
            raise ApiError(422, "Invalid address", "Give the clock's IP address or host name.")
        try:
            done = setup.setup(host, body.get("preset"))
        except ValueError as exc:
            raise ApiError(422, "No clock there", str(exc)) from None
        self.host, self.config_path = done["host"], config.path()
        return done

    def appearance(self, body):
        """Change only the [appearance] table: LED theme and the UI palette it may follow.

        Nothing is sent to the clock's settings; the service restarts to redraw its screens.
        """
        if not self.config_path:
            raise ApiError(409, "No tc002.toml", "Run `tc002 setup --config <path>` first.")
        before = self._settings()
        data = config.to_data(before)
        data["appearance"] = {
            **data["appearance"],
            **{k: body[k] for k in ("led_theme", "ui_palette") if k in body},
        }
        try:
            settings = config.parse(data, str(self.config_path))
        except config.ConfigError as exc:
            raise ApiError(422, "Invalid settings", str(exc)) from None
        config_writer.save(settings, self.config_path)
        return {
            "appearance": settings.appearance,
            "ledTheme": settings.led_theme,
            # only a change the clock can see is worth redrawing every screen for
            "serviceRestarted": settings.led_theme != before.led_theme and launchd.restart(),
        }

    def integration(self, action):
        try:
            return host_actions.run(action)
        except KeyError:
            raise ApiError(404, "Not found", f"No integration action {action!r}.") from None

    def log(self, query):
        return {"path": str(launchd.LOG), "text": host_actions.log_tail()}

    def reveal(self, body):
        targets = {"config": self.config_path, "log": launchd.LOG}
        target = targets.get(body.get("what"))
        if target is None:
            raise ApiError(422, "Nothing to show", "Choose the config file or the log.")
        host_actions.reveal(target)
        return {"revealed": str(target)}

    def led(self):
        """Pixel fonts and LED palette, so browser previews draw exactly what the clock would."""
        return {
            "font": {"big": font.BIG, "small": font.SMALL},
            "palette": hex_palette(),
            "size": {"width": WIDTH, "height": HEIGHT},
        }

    def cities(self, query):
        return cities.search(query.get("q", ""), query.get("lang", "en"))

    def preview(self, name, query):
        """LED mock-up GIF bytes for an example screen or a message draft.

        Screens are drawn in the saved LED theme, or in `?theme=` (a draft not yet saved);
        messages keep the colour they were given.
        """
        theme = query.get("theme") if query.get("theme") in themes.THEMES else None
        theme = theme or self._settings().led_theme
        if name == "text":
            anim, theme = (
                message.text_animation(
                    query.get("text", "TEXT")[: message.MAX_CHARS], query.get("color", "white")
                )[0],
                themes.CLASSIC,
            )
        elif name == "alert":
            anim = message.alert_animation(
                query.get("text", "DONE")[: message.ALERT_MAX_CHARS],
                query.get("kind", "done"),
                query.get("color"),
            )
            theme = themes.CLASSIC
        elif name.removeprefix("live-") in LIVE_SCREENS and name.startswith("live-"):
            screen = SCREENS[name.removeprefix("live-")]()
            anim = screen.render(screen.sample())
        elif name.startswith("builtin-"):
            try:
                anim = builtin_previews.render(name.removeprefix("builtin-"))
            except ValueError:
                raise ApiError(404, "Unknown preview", f"No built-in app {name!r}.") from None
        else:
            anims = examples()
            if name not in anims:
                raise ApiError(404, "Unknown preview", f"No preview named {name!r}.")
            anim = anims[name]
        return mockup.led_gif(anim, theme)

    # -- writes -------------------------------------------------------------------

    def save_config(self, data, restart=True):
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
        result["serviceRestarted"] = launchd.restart() if restart else False
        return result

    def quick(self, body):
        """Quick settings (brightness, volume, …): merged into the saved tc002.toml and applied
        at once, leaving any unsaved draft in the UI alone. The rotation is untouched, so the
        service is not restarted."""
        patch = body.get("display")
        if not isinstance(patch, dict) or not patch:
            raise ApiError(422, "Nothing to change", 'Send {"display": {...}}.')
        data = config.to_data(self._settings())
        display = dict(data["display"])
        for key, value in patch.items():
            if key == "brightness" and isinstance(value, dict):
                current = (self._clock_state_settings() or {}).get("brightness", {})
                value = {**current, **display.get("brightness", {}), **value}
            display[key] = value
        data["display"] = display
        return self.save_config(data, restart=False)

    def _clock_state_settings(self):
        if not self.host:
            return None
        try:
            return self._device().config()
        except DeviceError:
            return None

    def apply_preset(self, body):
        """The draft with a preset's rotation applied; the UI decides when to save it."""
        try:
            return {"data": presets.apply(body.get("data") or {}, body.get("preset"))}
        except ValueError as exc:
            raise ApiError(422, "Unknown preset", str(exc)) from None

    def live(self, body):
        """Put a draft on the clock without saving it, and keep the rotation off the screen."""
        data, focus = body.get("data"), body.get("focus") or {}
        try:
            settings = config.parse(data or {}, "draft")
        except config.ConfigError as exc:
            raise ApiError(422, "Invalid settings", str(exc).split(": ", 1)[-1]) from None
        dev = self._device()
        hold.hold(hold.LIVE_SECONDS)
        changes = sync.apply(dev, settings, self.state_dir)
        if focus:
            self.show(focus)
        return {"changes": changes, "heldFor": hold.LIVE_SECONDS}

    def live_stop(self, body):
        """Put the saved tc002.toml back on the clock and hand the screen back to the rotation."""
        hold.release()
        if not self.host:
            return {"changes": []}
        return {"changes": sync.apply(self._device(), self._settings(), self.state_dir)}

    def show(self, body):
        dev = self._device()
        if screen := body.get("screen"):
            if screen not in SCREENS:
                raise ApiError(422, "Unknown screen", f"No screen named {screen!r}.")
            # The background service may not run this screen (yet): put one frame on the
            # clock first, so switching to it cannot fail with "app not found".
            if screen not in dev.apps():
                live = SCREENS[screen]()
                frames = live.render(live.sample())
                dev.push(screen, frames.payload(theme=self._settings().led_theme))
            dev.switch_custom(screen)
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
    if settings.rotation and cfg.get("carouselSpeed"):
        drift.append("display.carouselSpeed")
    return drift
