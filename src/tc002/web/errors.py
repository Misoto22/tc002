"""The web front end's errors: its own `ApiError` (a malformed request), and the HTTP
status each application error becomes. The server sends both as RFC 9457 problems."""

from ..app import errors


class ApiError(Exception):
    """A request this front end refuses before it reaches App (bad JSON, wrong shape)."""

    def __init__(self, status, title, detail, errors=None):
        super().__init__(detail)
        self.status, self.title, self.detail, self.errors = status, title, detail, errors


STATUS = [  # most specific first
    (errors.NotConfigured, 409),
    (errors.Conflict, 409),
    (errors.NotFound, 404),
    (errors.InvalidRequest, 422),
    (errors.ServiceUnavailable, 502),
    (errors.CommandFailed, 500),
]


def problem_of(exc):
    """(status, title, detail, errors) for an AppError."""
    if isinstance(exc, errors.ClockUnreachable):
        if exc.status is None:
            return 502, "Clock unreachable", exc.detail, None
        if exc.status == 404:
            return 404, "Not on the clock", f"The clock has no such app: {exc.detail}", None
        return 502, "Clock refused the request", exc.detail, None
    status = next((code for kind, code in STATUS if isinstance(exc, kind)), 500)
    return status, exc.title, exc.detail, exc.errors
