"""HTTPS transport implementation using the ``requests`` library only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import requests

from otp_verification.exceptions import ConfigurationException, SecurityException
from otp_verification.transport.exceptions import (
    TransportAuthenticationError,
    TransportConnectionError,
    TransportError,
    TransportRateLimitError,
    TransportTimeoutError,
    TransportUnavailableError,
)


@dataclass(frozen=True)
class HttpTransportResult:
    """Parsed transport response without provider-specific interpretation."""

    status_code: int
    payload: Mapping[str, Any] | None
    raw_text: str


class RequestsHttpTransport:
    """Reusable HTTPS JSON POST transport.

    Retry is intentionally disabled. Providers translate transport errors into
    the OTP provider exception hierarchy.
    """

    def __init__(self, *, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()

    def post_json(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> HttpTransportResult:
        """Execute an HTTPS JSON POST and return a parsed result."""

        if not url:
            raise ConfigurationException("Transport URL is required.")
        if not str(url).lower().startswith("https://"):
            raise SecurityException("OTP provider transport requires HTTPS URLs only.")
        if timeout_seconds <= 0:
            raise ConfigurationException("Transport timeout_seconds must be > 0.")

        try:
            response = self._session.post(
                url,
                headers=dict(headers),
                json=dict(payload),
                timeout=timeout_seconds,
                allow_redirects=False,
            )
        except requests.Timeout as exc:
            raise TransportTimeoutError("HTTP request timed out.") from exc
        except requests.SSLError as exc:
            raise TransportConnectionError("TLS/SSL failure during HTTP request.") from exc
        except requests.ConnectionError as exc:
            raise TransportConnectionError("Connection failure during HTTP request.") from exc
        except requests.RequestException as exc:
            raise TransportError("Unexpected HTTP transport failure.") from exc

        parsed: Mapping[str, Any] | None
        try:
            parsed = response.json() if response.content else None
            if parsed is not None and not isinstance(parsed, dict):
                parsed = {"value": parsed}
        except ValueError:
            parsed = None

        status = int(response.status_code)
        if status in {401, 403}:
            raise TransportAuthenticationError(
                "Provider authentication/authorization failed.",
                status_code=status,
            )
        if status == 429:
            raise TransportRateLimitError(
                "Provider rate limit exceeded.",
                status_code=status,
            )
        if status in {408, 504}:
            raise TransportTimeoutError(
                "Provider request timed out.",
                status_code=status,
            )
        if status in {500, 502, 503}:
            raise TransportUnavailableError(
                "Provider service unavailable.",
                status_code=status,
            )
        if status >= 400:
            raise TransportError(
                f"Provider HTTP error status {status}.",
                status_code=status,
            )

        return HttpTransportResult(
            status_code=status,
            payload=parsed,
            raw_text=response.text or "",
        )
