"""API actions on this Mac and the services screens use: Claude Code and the service,
the log, Finder, social tokens for the clock, connection secrets and trying a screen.

Mixed into web.api.Api; the work itself is in host_actions.py, keychain.py and
connections.py."""

import subprocess

from .. import builtins, connections, device_settings, keychain
from ..device import CATEGORY_ENDPOINTS
from ..integrations import launchd
from ..screens import SCREENS, build
from . import host_actions
from .errors import ApiError


class HostActions:
    def _connections(self):
        try:
            return connections.status(self._settings_or_none())
        except OSError, subprocess.SubprocessError:
            return {}  # no Keychain here (not macOS): the page says so

    def save_secret(self, body):
        """Save (or with an empty value, remove) one connection secret in the Keychain."""
        name, field = body.get("connection"), body.get("field")
        if not connections.CONNECTIONS.get(name, {}).get(field):
            raise ApiError(422, "Invalid settings", "That is not a secret of a known connection.")
        value = str(body.get("value") or "").strip()
        key = connections.secret_name(name, field)
        if value:
            try:
                keychain.save(key, value)
            except (OSError, ValueError) as exc:
                raise ApiError(422, "Invalid settings", str(exc)) from None
        else:
            keychain.delete(key)
        return {"saved": bool(value)}

    def try_screen(self, body):
        """Sample one screen now and say whether it works, without touching the clock."""
        name = body.get("screen")
        if name not in SCREENS:
            raise ApiError(422, "Unknown screen", f"No screen named {name!r}.")
        try:
            build(name, self._settings_or_none()).sample()
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            return {"ok": False, "error": str(exc)[:200]}
        return {"ok": True}

    def social_token(self, body):
        """Hand a social app its OAuth token. Write-only: sent to the clock and forgotten;
        it is not logged, stored, or ever read back (the UI only learns that one is set)."""
        app, token = body.get("app"), body.get("token")
        if app not in device_settings.TOKEN_APPS:
            raise ApiError(
                422, "Invalid settings", f"Only {device_settings.TOKEN_APPS} take a token."
            )
        if not isinstance(token, str) or not token.strip() or len(token) > 4096:
            raise ApiError(422, "Invalid settings", "Paste the token the platform gave you.")
        dev = self._device()
        _, _, infos_key, order_key = CATEGORY_ENDPOINTS["social"]
        cfg = dev.category_config("social")
        infos = cfg.get(infos_key, {})
        infos.setdefault(app, {})["token"] = token.strip()
        order = cfg.get(order_key) or builtins.full_order("social")
        dev.set_category_config("social", {infos_key: infos, order_key: order})
        return {"app": app, "tokenSet": True}

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
