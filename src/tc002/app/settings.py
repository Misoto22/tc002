"""Use cases that change settings: tc002.toml (always validated first, written under
one lock, never over a newer file), and the clock's own settings that follow from it."""

from .. import config
from ..clock import builtins, sync
from ..clock.device import CATEGORY_ENDPOINTS, DeviceError
from ..config import presets, writer
from ..host import launchd
from ..state import hold
from . import catalog
from .errors import Conflict, InvalidRequest, InvalidSettings


class Configure:
    # -- tc002.toml ----------------------------------------------------------------

    def save_config(self, data, restart=True, expected=None):
        """Validate, write tc002.toml, push it to the clock, reload the service.

        `expected` is the version the caller read (config_version()); when the file has
        changed since (another tab, the CLI, an editor) nothing is written (Conflict)."""
        self._need_config_file()
        settings = self._parse(data)
        with writer.WRITE_LOCK:
            if expected is not None and expected != self.config_version():
                raise Conflict(
                    "Config changed",
                    "tc002.toml was changed elsewhere since this page loaded it, so it was "
                    "not overwritten. Your edits are kept: review them and save again.",
                )
            writer.save(settings, self.config_path)
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
        with writer.WRITE_LOCK:
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
        with writer.WRITE_LOCK:
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
            writer.save(settings, self.config_path)
            version = self.config_version()
        return {
            "appearance": settings.appearance,
            "ledTheme": settings.led_theme,
            "version": version,
            # only a change the clock can see is worth redrawing every screen for
            "serviceRestarted": settings.led_theme != before.led_theme and launchd.restart(),
        }

    def apply_preset(self, data, preset):
        """A tc002.toml draft with a preset's rotation applied; nothing is saved."""
        try:
            return {"data": presets.apply(data or {}, preset)}
        except ValueError as exc:
            raise InvalidRequest("Unknown preset", str(exc)) from None

    # -- the clock ------------------------------------------------------------------

    def apply(self):
        """Make the clock match tc002.toml (saving its original layout first)."""
        return sync.apply(self.device(), self.settings(), self.state_dir)

    def restore(self):
        """Put back the built-in apps and settings saved before tc002 first changed them."""
        return str(sync.restore(self.device(), self.state_dir))

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

    def live_stop(self):
        """Put the saved tc002.toml back on the clock and hand the screen to the rotation."""
        hold.release()
        if not self.host:
            return {"changes": []}
        return {"changes": sync.apply(self.device(), self.settings(), self.state_dir)}

    def set_social_token(self, app, token):
        """Hand a social app its OAuth token. Write-only: sent to the clock and forgotten;
        it is not logged, stored, or ever read back (callers only learn that one is set)."""
        if app not in catalog.TOKEN_APPS:
            raise InvalidSettings("Invalid settings", f"Only {catalog.TOKEN_APPS} take a token.")
        if not isinstance(token, str) or not token.strip() or len(token) > 4096:
            raise InvalidSettings("Invalid settings", "Paste the token the platform gave you.")
        dev = self.device()
        _, _, infos_key, order_key = CATEGORY_ENDPOINTS["social"]
        cfg = dev.category_config("social")
        infos = cfg.get(infos_key, {})
        infos.setdefault(app, {})["token"] = token.strip()
        order = cfg.get(order_key) or builtins.full_order("social")
        dev.set_category_config("social", {infos_key: infos, order_key: order})
        return {"app": app, "tokenSet": True}
