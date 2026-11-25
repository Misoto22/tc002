"""Errors the application layer raises. They say what went wrong, not how to show it:
the CLI prints `detail`, the web API turns them into RFC 9457 problems, the MCP server
into tool errors."""

from ..device import DeviceError


class AppError(Exception):
    """A use case could not be carried out. `title` is short, `detail` says what to do."""

    def __init__(self, title, detail, errors=None):
        super().__init__(detail)
        self.title, self.detail, self.errors = title, detail, errors


class NotConfigured(AppError):
    """No clock address, or no tc002.toml, to act on."""


class Conflict(AppError):
    """tc002.toml changed elsewhere since the caller read it; nothing was written."""


class InvalidRequest(AppError):
    """The arguments name nothing that exists or make no sense (unknown screen, empty text)."""


class InvalidSettings(InvalidRequest):
    """Settings that tc002.toml's validation rejects; nothing was written."""


class ClockUnreachable(AppError, DeviceError):
    """The clock did not answer or refused. Also a DeviceError, so code that already
    handles those (and their HTTP `status`) keeps working."""

    def __init__(self, detail, status=None):
        AppError.__init__(self, "Clock unreachable", detail)
        self.status = status
