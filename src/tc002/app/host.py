"""Use cases on this Mac: the background service, Claude Code's hooks and status line,
connection secrets in the Keychain, the log, Finder."""

import json

from ..host import claude_hooks, connections, executable, finder, keychain, launchd, statusline
from ..state import sessions
from .errors import ClockUnreachable, InvalidRequest, InvalidSettings, NotFound

LOG_LINES = 200
# the settings UI's Integrations page: action name -> App method
INTEGRATIONS = {
    "connect-claude": "connect_claude",
    "disconnect-claude": "disconnect_claude",
    "restart-service": "service_restart",
}


class Host:
    # -- the background service -----------------------------------------------------

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

    def log(self, lines=LOG_LINES):
        return {"path": str(launchd.LOG), "text": launchd.log_tail(lines)}

    # -- Claude Code ----------------------------------------------------------------

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

    def record_hook(self, payload_text):
        """A Claude Code hook's JSON (as it came on stdin) -> that session's state file."""
        sessions.record_hook(json.loads(payload_text or "{}"))

    def record_event(self, kind):
        """`tc002 event done|wait|clear`: mark the latest session by hand."""
        sessions.record_manual(kind)

    def statusline(self, raw):
        """Save the plan limits in Claude Code's status line input, then return what the
        user's own status line command prints (bytes in, bytes out)."""
        return statusline.run(raw)

    # -- setting tc002 up on this Mac -----------------------------------------------

    def install(self):
        """Hooks and status line, the layout (if the clock answers), the service."""
        result = {"claude": self.connect_claude(), "layout": {"applied": False}}
        if not self.host:
            result["layout"]["error"] = "no clock configured"
        else:
            try:
                result["layout"] = {"applied": True, "changes": self.apply()}
            except ClockUnreachable as exc:
                result["layout"]["error"] = exc.detail
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
        except ClockUnreachable as exc:
            result["error"] = exc.detail
        except FileNotFoundError as exc:  # tc002 never changed this clock's layout
            result["error"] = str(exc)
        return result

    # -- the settings UI's Integrations page ----------------------------------------

    def integration(self, action):
        """One of a fixed set of actions on this Mac, by the name the UI uses."""
        if action == "install-service":
            done = self.service_install()
            return {"installed": done["installed"], "service": done["status"]}
        if action not in INTEGRATIONS:
            raise NotFound("Not found", f"No integration action {action!r}.")
        return getattr(self, INTEGRATIONS[action])() or {}

    def reveal(self, what):
        """Show tc002.toml ("config") or the service log ("log") in the Finder."""
        targets = {"config": self.config_path, "log": launchd.LOG}
        target = targets.get(what)
        if target is None:
            raise InvalidRequest("Nothing to show", "Choose the config file or the log.")
        finder.reveal(target)
        return {"revealed": str(target)}

    # -- connection secrets ---------------------------------------------------------

    def save_secret(self, connection, field, value):
        """Save (or with an empty value, remove) one connection secret in the Keychain."""
        if not connections.CONNECTIONS.get(connection, {}).get(field):
            raise InvalidSettings("Invalid settings", "That is not a secret of a known connection.")
        value = str(value or "").strip()
        key = connections.secret_name(connection, field)
        if value:
            try:
                keychain.save(key, value)
            except (OSError, ValueError) as exc:
                raise InvalidSettings("Invalid settings", str(exc)) from None
        else:
            keychain.delete(key)
        return {"saved": bool(value)}
