"""The application layer: every use case tc002 offers, in one place.

The CLI (`cli/`), the web API (`web/api.py`) and the MCP server (`mcp/`) are thin
front ends over `App`: they turn their input into a method call and its result (a plain
dict, list or string) into their output. `App` is the only code above `sync`, `night`,
`launchd` and `Device` that front ends call, so "save, apply to the clock, restart the
service" or "is the clock healthy?" mean the same thing everywhere.

Errors are typed (`app.errors`): `NotConfigured`, `InvalidRequest`/`InvalidSettings`
and `ClockUnreachable` (also a `DeviceError`, carrying its HTTP status).
"""

import functools
import json
import threading
import time

from .. import builtins, config, config_writer, night, sync
from ..device import CATEGORY_ENDPOINTS, MIN_FIRMWARE, Device, DeviceError, firmware
from ..integrations import claude_hooks, executable, launchd, statusline
from ..runtime import focus as focus_timer
from ..runtime import hold, sessions
from ..runtime.output import Output
from ..screens import NETWORKED, SCREENS, build, message
from . import state
from .errors import (
    AppError,
    ClockUnreachable,
    Conflict,
    InvalidRequest,
    InvalidSettings,
    NotConfigured,
)

__all__ = [
    "App",
    "AppError",
    "ClockUnreachable",
    "Conflict",
    "InvalidRequest",
    "InvalidSettings",
    "NotConfigured",
]

FOCUS_MINUTES = (1, 180)
MESSAGE_HOLD = 10  # seconds a short played message stays before it is removed


def _clock(method):
    """Report a clock that does not answer as ClockUnreachable, whatever the method did."""

    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except ClockUnreachable:
            raise
        except DeviceError as exc:
            raise ClockUnreachable(str(exc), exc.status) from exc

    return wrapper


class App:
    """One clock (`host`) and one tc002.toml (`config_path`).

    `preview` (a directory) sends text, alerts and screens to LED mock-up GIFs instead of
    the clock. `device` is a factory for the clock client, for tests and for front ends
    that want their own (by default a `Device(host, timeout)`).
    """

    def __init__(
        self, host=None, config_path=None, state_dir=None, *, timeout=5, preview=None, device=None
    ):
        self.host, self.config_path = host, config_path
        self.state_dir = state_dir or config.STATE_DIR
        self.timeout, self.preview = timeout, preview
        self._device_factory = device

    @classmethod
    def local(cls, host=None, config_path=None, **kwargs):
        """The clock and tc002.toml this Mac was set up with (`tc002 setup`, $TC002_*)."""
        chosen = config_path or config.path()
        return cls(config.host(host), chosen, **kwargs)

    # -- plumbing -----------------------------------------------------------------

    def new_device(self):
        if not self.host:
            raise NotConfigured("No clock configured", "Run `tc002 setup --host <IP>` first.")
        return Device(self.host, timeout=self.timeout)

    def device(self):
        return self._device_factory() if self._device_factory else self.new_device()

    def settings(self):
        """tc002.toml as it is on disk now (built-in defaults when there is none)."""
        return config.load(self.config_path)

    def settings_or_none(self):
        try:
            return self.settings()
        except config.ConfigError:
            return None

    def config_version(self):
        """A fingerprint of tc002.toml on disk; pass it back to save_config as `expected`."""
        return config_writer.version(self.config_path) if self.config_path else None

    def led_theme(self):
        """The saved LED theme; classic until a readable tc002.toml says otherwise."""
        from ..render import themes

        settings = self.settings_or_none()
        return settings.led_theme if settings else themes.CLASSIC

    def _need_config_file(self):
        if not self.config_path:
            raise NotConfigured("No tc002.toml", "Run `tc002 setup --config <path>` first.")

    def _parse(self, data, source=None):
        try:
            return config.parse(data, source or str(self.config_path))
        except config.ConfigError as exc:
            problems = str(exc).split(": ", 1)[-1].split("; ")
            raise InvalidSettings(
                "Invalid settings",
                "tc002.toml was not changed.",
                [{"field": "config", "message": p} for p in problems],
            ) from None

    # -- reads --------------------------------------------------------------------

    def status(self):
        """A short summary: clock reachable?, service, screen dark?, focus, live hold."""
        settings = self.settings_or_none()
        clock = {"host": self.host, "online": False}
        if not self.host:
            clock["error"] = "no clock configured"
        else:
            try:
                dev = self.device()
                base = dev.base_info()
                clock |= {
                    "online": True,
                    "firmware": base.get("appVer"),
                    "customApps": dev.apps(),
                }
            except DeviceError as exc:
                clock["error"] = str(exc)
        return {
            "clock": clock,
            "config": settings.source if settings else "tc002.toml is invalid",
            "service": launchd.status().splitlines()[0],
            "night": night.status(settings),
            "focus": self.focus_now(),
            "liveHoldSeconds": round(hold.active()),
        }

    def screens(self):
        """Every live screen tc002 can draw and every built-in app, and which are in use."""
        settings = self.settings_or_none() or config.Settings()
        seconds = {s.screen or s.builtin: s.seconds for s in settings.schedule if s}
        return {
            "screens": [
                {
                    "name": name,
                    "enabled": name in settings.screens,
                    "rotationSeconds": seconds.get(name),
                    "networked": name in NETWORKED,
                }
                for name in SCREENS
            ],
            "builtins": [
                {
                    "name": key,
                    "category": b.category,
                    "kept": key in settings.keep_builtins,
                    "rotationSeconds": seconds.get(key),
                }
                for key, b in builtins.CATALOGUE.items()
            ],
            "rotationMode": settings.rotation_mode,
        }

    def now_showing(self):
        """What tc002 is driving the screen with. The clock itself does not report which
        app is on screen, so this is tc002's side: night, live hold, focus, rotation."""
        settings = self.settings_or_none() or config.Settings()
        dark = night.status(settings)
        held = round(hold.active())
        if dark["dark"]:
            driver = "night: the screen is fully dark"
        elif held:
            driver = f"live preview from the settings UI ({held}s left)"
        else:
            driver = f"rotation ({settings.rotation_mode})"
        return {
            "driver": driver,
            "night": dark,
            "liveHoldSeconds": held,
            "focus": self.focus_now(),
            "rotation": [
                {"screen": s.screen, "builtin": s.builtin, "seconds": s.seconds}
                for s in settings.schedule
                if s
            ],
            "service": launchd.status().splitlines()[0],
        }

    def config_data(self):
        """tc002.toml as a JSON document (what save_config takes back) and its path."""
        return {
            "path": str(self.config_path) if self.config_path else None,
            "data": config.to_data(self.settings()),
            "version": self.config_version(),
        }

    def clock_state(self, settings=None):
        """Everything the clock reports that tc002 manages, plus drift from tc002.toml.
        Never raises for an offline clock: `{"online": False, "error": ...}`."""
        if not self.host:
            return {"online": False, "error": "no clock configured"}
        return state.clock_state(self.device(), self.host, settings or self.settings())

    def integrations(self):
        try:
            exe = executable()
            hooks, wrapped = claude_hooks.status(exe), statusline.status(exe)
        except RuntimeError as exc:
            hooks, wrapped = {"error": str(exc)}, False
        return {"service": launchd.status(), "hooks": hooks, "statusline": wrapped}

    def checks(self):
        """`tc002 doctor`: [{"name", "ok": True/False/None (warning), "detail"}]."""
        out = []

        def check(ok, name, detail=""):
            out.append({"name": name, "ok": ok, "detail": detail})

        settings = self.settings_or_none()
        check(settings is not None, "config", settings.source if settings else "invalid")
        if not self.host:
            check(False, "clock", "no host: run `tc002 setup --host <IP>`")
        else:
            try:
                dev = self.device()
                base = dev.info()["base"]
                fw = firmware(base.get("appVer"))
                check(True, "clock", f"{dev.base} firmware {base.get('appVer')}")
                check(
                    fw >= MIN_FIRMWARE or None,
                    "firmware",
                    "screen switching supported" if fw >= MIN_FIRMWARE else "update for switching",
                )
                check(True, "custom apps", ", ".join(dev.apps()) or "(none)")
            except DeviceError as exc:
                check(False, "clock", str(exc))
        status = launchd.status()
        check(status.startswith("state: running") or None, "service", status.splitlines()[0])
        try:
            hook_state = claude_hooks.status(executable())
            check(all(hook_state.values()) or None, "hooks", json.dumps(hook_state))
        except RuntimeError as exc:
            check(None, "hooks", str(exc))
        try:
            wrapped = statusline.status(executable())
        except RuntimeError:
            wrapped = False
        check(wrapped or None, "status line", "saves plan limits")
        known = sessions.load()
        latest = (
            f"{known[0].project} {known[0].state} {time.time() - known[0].since:.0f}s ago"
            if known
            else ""
        )
        check(True, "sessions", f"{len(known)} known, latest: {latest}" if known else "none yet")
        return out

    @_clock
    def base_info(self):
        """Firmware, network and serial: the cheapest call that proves the clock is there."""
        return self.device().base_info()

    @_clock
    def info(self):
        return self.device().info()

    @_clock
    def custom_apps(self):
        return self.device().apps()

    @_clock
    def layout(self):
        dev = self.device()
        return {
            "categories": builtins.snapshot(dev),
            "carouselSpeed": dev.config().get("carouselSpeed"),
            "keepBuiltins": list(self.settings().keep_builtins),
        }

    def night_status(self):
        return night.status(self.settings_or_none())

    def focus_now(self):
        now = focus_timer.current()
        return {"phase": now[0], "left": round(now[1])} if now else None

    # -- the screen ---------------------------------------------------------------

    @_clock
    def show(self, screen=None, builtin=None):
        """Switch the clock to a live screen or a built-in app now. The rotation takes
        over again at its next slot."""
        dev = self.device()
        if screen:
            if screen not in SCREENS:
                raise InvalidRequest("Unknown screen", f"No screen named {screen!r}.")
            # The background service may not run this screen (yet): put one frame on the
            # clock first, so switching to it cannot fail with "app not found".
            if screen not in dev.apps():
                live = build(screen, self.settings_or_none())
                frames = live.render(live.sample())
                dev.push(screen, frames.payload(theme=self.led_theme()))
            dev.switch_custom(screen)
            return {"ok": True, "screen": screen}
        if builtin:
            try:
                app = builtins.lookup(builtin)
            except ValueError as exc:
                raise InvalidRequest("Unknown built-in app", str(exc)) from None
            dev.switch_builtin(app.category, app.index)
            return {"ok": True, "builtin": builtin}
        raise InvalidRequest("Nothing to show", "Send `screen` or `builtin`.")

    def output(self, device=None):
        return Output(device, self.preview)

    def _live_device(self):
        return None if self.preview else self.device()

    @_clock
    def send_text(self, text, color="white", app="msg", passes=2, show=False):
        """Play text and wait for it (CLI). Short text stays; long text scrolls `passes`
        times and is then removed."""
        dev = self._live_device()
        out = self.output(dev)
        segments = message.text_animation(text, color)
        if len(segments) == 1:
            out.show(app, segments[0])
        else:  # long text: segments back to back, then leave the clock clean
            for _ in range(max(1, passes)):
                for seg in segments:
                    out.show(app, seg)
                    if dev is None:
                        break
                    time.sleep(seg.duration_s())
            if dev is not None:
                out.remove(app)
                return {"app": app, "removed": True}
        if show and dev is not None:
            dev.switch_custom(app)
        return {"app": app, "removed": False}

    @_clock
    def send_alert(self, text, kind="done", color=None, app="alert", seconds=10, keep=False):
        """Show an alert and wait `seconds` before removing it (CLI), unless `keep`."""
        dev = self._live_device()
        out = self.output(dev)
        out.show(app, message.alert_animation(text, kind, color))
        if dev is None:
            return {"app": app, "removed": False}
        dev.switch_custom(app)
        if not keep:
            time.sleep(seconds)
            out.remove(app)
        return {"app": app, "removed": not keep}

    def play_message(self, text, type="text", kind="done", color=None):
        """Text or alert, played in the background so the caller returns at once; the
        clock goes back to the rotation when it ends."""
        dev = self.device()
        text = str(text or "").strip()
        if not text:
            raise InvalidRequest("Empty message", "Type something to send.")
        if type == "alert":
            if kind not in message.ICONS:
                choices = ", ".join(message.ICONS)
                raise InvalidRequest("Unknown alert kind", f"Choose one of {choices}.")
            segments, app = [message.alert_animation(text, kind, color)], "alert"
        else:
            segments, app = message.text_animation(text, color or "white"), "msg"
        threading.Thread(target=_play, args=(dev, app, segments), daemon=True).start()
        return {"ok": True, "app": app, "seconds": round(sum(s.duration_s() for s in segments))}

    @_clock
    def remove_apps(self, names=None):
        """Remove custom apps from the clock (all of them when none are named)."""
        dev = self.device()
        names = list(names or dev.apps())
        for name in names:
            dev.remove(name)
        return names

    def watch(self, once=False):
        """Run the screens and the rotation in the foreground until stopped."""
        from ..runtime import watcher

        dev = None if (self.preview or not self.host) else self.device()
        watcher.watch(dev, self.settings(), self.preview, once=once)

    # -- night --------------------------------------------------------------------

    @_clock
    def screen_off(self, until_morning=False):
        """Screen fully dark now, until turned on (or until the night schedule's end)."""
        settings = self.settings_or_none()
        until = night.until_morning(settings) if until_morning else None
        return night.turn_off(self.device(), settings, until)

    @_clock
    def screen_on(self):
        """Light the screen now; inside the night schedule it stays lit until it ends."""
        return night.turn_on(self.device(), self.settings_or_none())

    # -- focus timer --------------------------------------------------------------

    def focus_start(self, minutes=None):
        settings = self.settings_or_none()
        screen = build("focus", settings)
        minutes = screen.minutes if minutes is None else minutes
        low, high = FOCUS_MINUTES
        if not isinstance(minutes, int) or isinstance(minutes, bool) or not low <= minutes <= high:
            raise InvalidSettings(
                "Invalid settings", f"Minutes must be a whole number from {low} to {high}."
            )
        focus_timer.start(minutes, screen.break_minutes)
        enabled = settings is not None and "focus" in settings.screens
        return {
            "running": True,
            "minutes": minutes,
            "break": screen.break_minutes,
            "screenEnabled": enabled,
        }

    def focus_stop(self):
        focus_timer.stop()
        return {"running": False}

    # -- tc002.toml and the clock's settings --------------------------------------

    def save_config(self, data, restart=True, expected=None):
        """Validate, write tc002.toml, push it to the clock, reload the service.

        `expected` is the version the caller read (config_version()); when the file has
        changed since (another tab, the CLI, an editor) nothing is written (Conflict)."""
        self._need_config_file()
        settings = self._parse(data)
        with config_writer.WRITE_LOCK:
            if expected is not None and expected != self.config_version():
                raise Conflict(
                    "Config changed",
                    "tc002.toml was changed elsewhere since this page loaded it, so it was "
                    "not overwritten. Your edits are kept: review them and save again.",
                )
            config_writer.save(settings, self.config_path)
            version = self.config_version()
        result = {
            "saved": str(self.config_path),
            "version": version,
            "changes": [],
            "applied": False,
        }
        if self.host:
            try:
                result["changes"] = sync.apply(self.device(), settings, self.state_dir)
                result["applied"] = True
            except DeviceError as exc:
                result["error"] = f"saved, but the clock is unreachable: {exc}"
        result["serviceRestarted"] = launchd.restart() if restart else False
        return result

    def set_display(self, patch):
        """Merge `[display]` settings (brightness, volume, …) into the saved tc002.toml and
        apply them at once. The rotation is untouched, so the service is not restarted."""
        if not isinstance(patch, dict) or not patch:
            raise InvalidRequest("Nothing to change", "Give at least one display setting.")
        if any(key == "brightness" and isinstance(v, dict) for key, v in patch.items()):
            clock = (self._clock_settings() or {}).get("brightness", {})
        else:
            clock = {}
        # read and write under one lock: a concurrent save cannot land in between and be lost
        with config_writer.WRITE_LOCK:
            data = config.to_data(self.settings())
            display = dict(data["display"])
            for key, value in patch.items():
                if key == "brightness" and isinstance(value, dict):
                    value = {**clock, **display.get("brightness", {}), **value}
                display[key] = value
            data["display"] = display
            return self.save_config(data, restart=False)

    def _clock_settings(self):
        if not self.host:
            return None
        try:
            return self.device().config()
        except DeviceError:
            return None

    def set_appearance(self, led_theme=None, ui_palette=None):
        """Change only [appearance]; the service restarts if the LED theme changed."""
        self._need_config_file()
        with config_writer.WRITE_LOCK:
            before = self.settings()
            data = config.to_data(before)
            changes = {"led_theme": led_theme, "ui_palette": ui_palette}
            data["appearance"] = {
                **data["appearance"],
                **{k: v for k, v in changes.items() if v is not None},
            }
            try:
                settings = config.parse(data, str(self.config_path))
            except config.ConfigError as exc:
                raise InvalidSettings("Invalid settings", str(exc)) from None
            config_writer.save(settings, self.config_path)
            version = self.config_version()
        return {
            "appearance": settings.appearance,
            "ledTheme": settings.led_theme,
            "version": version,
            # only a change the clock can see is worth redrawing every screen for
            "serviceRestarted": settings.led_theme != before.led_theme and launchd.restart(),
        }

    @_clock
    def set_social_token(self, app, token):
        """Hand a social app its OAuth token. Write-only: sent to the clock and forgotten."""
        dev = self.device()
        _, _, infos_key, order_key = CATEGORY_ENDPOINTS["social"]
        cfg = dev.category_config("social")
        infos = cfg.get(infos_key, {})
        infos.setdefault(app, {})["token"] = token
        order = cfg.get(order_key) or builtins.full_order("social")
        dev.set_category_config("social", {infos_key: infos, order_key: order})
        return {"app": app, "tokenSet": True}

    @_clock
    def apply(self):
        """Make the clock match tc002.toml (saving its original layout first)."""
        return sync.apply(self.device(), self.settings(), self.state_dir)

    @_clock
    def restore(self):
        """Put back the built-in apps and settings saved before tc002 first changed them."""
        return str(sync.restore(self.device(), self.state_dir))

    @_clock
    def live(self, data, focus=None):
        """Put a draft on the clock without saving it; the rotation stays off the screen."""
        try:
            settings = config.parse(data or {}, "draft")
        except config.ConfigError as exc:
            raise InvalidSettings("Invalid settings", str(exc).split(": ", 1)[-1]) from None
        dev = self.device()
        hold.hold(hold.LIVE_SECONDS)
        changes = sync.apply(dev, settings, self.state_dir)
        if focus:
            self.show(focus.get("screen"), focus.get("builtin"))
        return {"changes": changes, "heldFor": hold.LIVE_SECONDS}

    @_clock
    def live_stop(self):
        """Put the saved tc002.toml back on the clock and hand the screen to the rotation."""
        hold.release()
        if not self.host:
            return {"changes": []}
        return {"changes": sync.apply(self.device(), self.settings(), self.state_dir)}

    # -- this Mac: the service and Claude Code -----------------------------------

    def service_status(self):
        return launchd.status()

    def service_install(self):
        installed = launchd.install(executable())
        return {"installed": installed, "plist": str(launchd.PLIST), "status": launchd.status()}

    def service_uninstall(self):
        launchd.uninstall()
        return {"plist": str(launchd.PLIST), "status": launchd.status()}

    def service_restart(self):
        return {"restarted": launchd.restart(), "service": launchd.status()}

    def claude_status(self):
        exe = executable()
        return {"hooks": claude_hooks.status(exe), "statusline": statusline.status(exe)}

    def connect_claude(self):
        """Add tc002's Claude Code hooks and wrap the status line (both idempotent)."""
        exe = executable()
        return {"hooks": claude_hooks.install(exe), "statusline": statusline.install(exe)}

    def disconnect_claude(self):
        exe = executable()
        return {"hooks": claude_hooks.uninstall(exe), "statusline": statusline.uninstall(exe)}

    def install(self):
        """Hooks and status line, the layout (if the clock answers), the service."""
        result = {"claude": self.connect_claude(), "layout": {"applied": False}}
        if not self.host:
            result["layout"]["error"] = "no clock configured"
        else:
            try:
                result["layout"] = {"applied": True, "changes": self.apply()}
            except DeviceError as exc:
                result["layout"]["error"] = str(exc)
        launchd.install(executable())
        result["service"] = launchd.status()
        return result

    def uninstall(self):
        """Stop the service, remove the hooks, restore the built-in apps."""
        launchd.uninstall()
        result = {"claude": self.disconnect_claude(), "restored": None}
        if not self.host:
            return result
        try:
            result["restored"] = self.restore()
        except (DeviceError, FileNotFoundError) as exc:
            result["error"] = str(exc)
        return result


def _play(dev, app, segments, hold=MESSAGE_HOLD):
    try:
        for seg in segments:
            dev.push(app, seg.payload())
            dev.switch_custom(app)
            time.sleep(max(seg.duration_s(), hold if len(segments) == 1 else 0))
        dev.remove(app)
    except DeviceError:
        pass  # best effort: the caller already reported the message as accepted
