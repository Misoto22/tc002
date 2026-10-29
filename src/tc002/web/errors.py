"""The one error type the API raises; the server turns it into an RFC 9457 problem."""


class ApiError(Exception):
    """Becomes an RFC 9457 problem response."""

    def __init__(self, status, title, detail, errors=None):
        super().__init__(detail)
        self.status, self.title, self.detail, self.errors = status, title, detail, errors
