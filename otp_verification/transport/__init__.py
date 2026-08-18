"""Reusable HTTP transport layer for OTP providers.

Provider-specific payload mapping must stay outside this package.
"""

from otp_verification.transport.http import HttpTransportResult, RequestsHttpTransport
from otp_verification.transport.exceptions import (
    TransportAuthenticationError,
    TransportConnectionError,
    TransportError,
    TransportRateLimitError,
    TransportTimeoutError,
    TransportUnavailableError,
)

__all__ = [
    "HttpTransportResult",
    "RequestsHttpTransport",
    "TransportAuthenticationError",
    "TransportConnectionError",
    "TransportError",
    "TransportRateLimitError",
    "TransportTimeoutError",
    "TransportUnavailableError",
]
