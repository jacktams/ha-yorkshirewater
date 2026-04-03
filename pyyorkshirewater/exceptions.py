"""Exceptions for pyyorkshirewater."""


class AuthError(Exception):
    """Base authentication error."""


class LoginError(AuthError):
    """Failed to log in with provided credentials."""


class TokenError(AuthError):
    """Failed to obtain or refresh access token."""


class ApiError(Exception):
    """Base API error."""


class UnauthorizedError(ApiError):
    """Request returned 401 - token may be expired."""


class RateLimitError(ApiError):
    """Request returned 429 - rate limited."""


class ServiceUnavailableError(ApiError):
    """Request returned 503 - service unavailable."""
