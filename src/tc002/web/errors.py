"""The API's errors: its own `ApiError`, and the HTTP status each application-layer error
(`tc002.app.errors`) becomes. The server turns both into RFC 9457 problems."""

from ..app.errors import Conflict, InvalidRequest, NotConfigured


class ApiError(Exception):
    """Becomes an RFC 9457 problem response."""

    def __init__(self, status, title, detail, errors=None):
        super().__init__(detail)
        self.status, self.title, self.detail, self.errors = status, title, detail, errors


def app_status(exc):
    """409 when there is nothing to act on yet, 422 for a bad request, else 500.
    (ClockUnreachable is a DeviceError and is mapped with those.)"""
    if isinstance(exc, NotConfigured | Conflict):
        return 409
    if isinstance(exc, InvalidRequest):
        return 422
    return 500
