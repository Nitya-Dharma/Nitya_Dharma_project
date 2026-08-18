"""Transport-layer exceptions (translated by providers before escaping)."""


class TransportError(Exception):
    """Base transport failure."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class TransportTimeoutError(TransportError):
    """Raised when an HTTP request times out."""


class TransportConnectionError(TransportError):
    """Raised for DNS/TLS/connection failures."""


class TransportUnavailableError(TransportError):
    """Raised when the remote service is unavailable."""


class TransportAuthenticationError(TransportError):
    """Raised for HTTP 401/403 authentication/authorization failures."""


class TransportRateLimitError(TransportError):
    """Raised for HTTP 429 rate-limit responses."""
