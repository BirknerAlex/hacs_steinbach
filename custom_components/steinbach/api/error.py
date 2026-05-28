"""Errors raised by the Tuya OpenAPI client."""


class ApiError(Exception):
    """Base class for Tuya OpenAPI errors."""


class AuthenticationError(ApiError):
    """Raised when authentication (token, signature, or permission) fails."""

    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)


class RequestError(ApiError):
    """Raised when an HTTP request to the Tuya OpenAPI fails."""

    def __init__(self, message: str = "Request failed"):
        self.message = message
        super().__init__(self.message)
