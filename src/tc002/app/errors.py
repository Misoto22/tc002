"""Errors the application layer raises. They say what went wrong, not how to show it:
the CLI prints `detail`, the web API turns them into RFC 9457 problems, the MCP server
into tool errors. Every App method raises only these (see `base.guarded`)."""


class AppError(Exception):
    """A use case could not be carried out. `title` is short, `detail` says what to do."""

    def __init__(self, title, detail, errors=None):
        super().__init__(detail)
        self.title, self.detail, self.errors = title, detail, errors


class NotConfigured(AppError):
    """No clock address, or no tc002.toml, to act on."""


class NotFound(AppError):
    """No such thing to act on (an integration action, a preview, a game)."""


class Conflict(AppError):
    """The state changed under the caller (tc002.toml edited elsewhere, no game running)."""


class InvalidRequest(AppError):
    """The arguments name nothing that exists or make no sense (unknown screen, empty text)."""


class InvalidSettings(InvalidRequest):
    """Settings that tc002.toml's validation rejects; nothing was written."""


class ClockUnreachable(AppError):
    """The clock did not answer, or refused. `status` is its HTTP status if it answered."""

    def __init__(self, detail, status=None):
        super().__init__("Clock unreachable", detail)
        self.status = status


class ServiceUnavailable(AppError):
    """A service on the network that a use case needs did not answer (a search service,
    Home Assistant)."""


class CommandFailed(AppError):
    """A command on this Mac failed (launchctl, open, networksetup); `detail` says what
    it printed."""
