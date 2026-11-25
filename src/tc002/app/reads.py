"""Use cases that only read: is everything healthy, what is on the clock, what is set."""

import json
import subprocess
import time
from pathlib import Path

from .. import config
from ..clock import builtins
from ..clock.device import MIN_FIRMWARE, DeviceError, firmware
from ..host import claude_hooks, connections, executable, launchd, statusline
from ..runtime import freshness, night
from ..screens import NETWORKED, SCREENS
from ..state import focus as focus_timer
from ..state import hold, sessions
from . import catalog, clock_report
from .agents import Agents


class Reads:
    # -- summaries ----------------------------------------------------------------

    def status(self):
        """A short summary: clock reachable?, service, screen dark?, focus, live hold."""
        settings = self.settings_or_none()
        clock = {"host": self.host, "online": False}
        if not self.host and not self._device_factory:
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

    def overview(self):
        """Everything the settings UI shows on load: tc002.toml, the clock, this Mac."""
        settings = self.settings()
        return {
            "night": night.status(settings),
            "config": {
                "path": str(self.config_path) if self.config_path else None,
                "shown": _home_relative(self.config_path),
                "data": config.to_data(settings),
                # sent back with a save: a file changed since is not overwritten
                "version": self.config_version(),
            },
            "clock": self.clock_state(settings),
            "integrations": self.integrations(),
            "agents": self.agents(),
            "freshness": freshness.read(),
            "focus": self.focus_now(),
            "connections": self.connections(),
            **catalog.ui(),
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
        """tc002.toml as a JSON document (what save_config takes back), its path and version."""
        return {
            "path": str(self.config_path) if self.config_path else None,
            "data": config.to_data(self.settings()),
            "version": self.config_version(),
        }

    def clock_state(self, settings=None):
        """Everything the clock reports that tc002 manages, plus drift from tc002.toml.
        Never raises for an offline clock: `{"online": False, "error": ...}`."""
        if not self.host and not self._device_factory:
            return {"online": False, "error": "no clock configured"}
        return clock_report.clock_state(self.device(), self.host, settings or self.settings())

    def integrations(self):
        try:
            exe = executable()
            hooks, wrapped = claude_hooks.status(exe), statusline.status(exe)
        except RuntimeError as exc:
            hooks, wrapped = {"error": str(exc)}, False
        return {"service": launchd.status(), "hooks": hooks, "statusline": wrapped}

    def connections(self):
        """Which connections (Home Assistant, calendars, ...) have their secrets set."""
        try:
            return connections.status(self.settings_or_none())
        except OSError, subprocess.SubprocessError:
            return {}  # no Keychain here (not macOS): the UI says so

    def agents(self):
        """Each coding-agent session's state and each agent's usage and limits."""
        if getattr(self, "_agents", None) is None:
            self._agents = Agents()  # keeps transcript readers between calls
        return self._agents.snapshot()

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
        if known:
            latest = f"{known[0].project} {known[0].state} {time.time() - known[0].since:.0f}s ago"
            check(True, "sessions", f"{len(known)} known, latest: {latest}")
        else:
            check(True, "sessions", "none yet")
        return out

    # -- the clock ----------------------------------------------------------------

    def base_info(self):
        """Firmware, network and serial: the cheapest call that proves the clock is there."""
        return self.device().base_info()

    def clock_check(self):
        """Ask the clock for its firmware and network now, and time the answer. Never
        raises for an offline clock: `{"ok": False, "error", "ms"}`."""
        started = time.monotonic()
        try:
            base = self.device().base_info()
        except DeviceError as exc:
            ms = round((time.monotonic() - started) * 1000)
            return {"ok": False, "error": str(exc)[:200], "ms": ms}
        return {
            "ok": True,
            "ms": round((time.monotonic() - started) * 1000),
            "facts": [
                ["firmware", str(base.get("appVer", "?"))],
                ["mcu", str(base.get("mcuVer", "?"))],
                ["ip", str(base.get("ip", self.host))],
                ["wifi", str(base.get("ssid", "?"))],
            ],
        }

    def info(self):
        return self.device().info()

    def custom_apps(self):
        return self.device().apps()

    def layout(self):
        dev = self.device()
        return {
            "categories": builtins.snapshot(dev),
            "carouselSpeed": dev.config().get("carouselSpeed"),
            "keepBuiltins": list(self.settings().keep_builtins),
        }

    # -- timers -------------------------------------------------------------------

    def night_status(self):
        return night.status(self.settings_or_none())

    def focus_now(self):
        now = focus_timer.current()
        return {"phase": now[0], "left": round(now[1])} if now else None


def _home_relative(path):
    """The config path as a person reads it: ~/… rather than the home directory."""
    if not path:
        return None
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home) :] if text.startswith(home + "/") else text
