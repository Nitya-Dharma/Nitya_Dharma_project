"""Secret-free provider result objects for orchestration callers.

These objects sit beside Task 1 ``ProviderResponse`` without redesigning the
``BaseOTPProvider`` interface. ``MockOTPProvider.send`` still returns
``ProviderResponse``; orchestration maps that response into ``ProviderResult``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

from otp_verification.enums import ProviderResultStatus
from otp_verification.exceptions import InvalidProviderResponseException
from otp_verification.interfaces.providers import ProviderResponse


@dataclass(frozen=True)
class ProviderResult:
    """Secret-free provider execution result.

    Fields intentionally exclude OTP, hashes, salts, and credentials.
    """

    status: str
    provider_name: str
    provider_message: str
    provider_reference: str
    timestamp: datetime

    def is_success(self) -> bool:
        return self.status == ProviderResultStatus.SUCCESS


def validate_provider_result(result: ProviderResult) -> ProviderResult:
    """Validate a provider result object and reject malformed payloads."""

    if not isinstance(result, ProviderResult):
        raise InvalidProviderResponseException("Provider result must be a ProviderResult.")
    if not result.provider_name:
        raise InvalidProviderResponseException("Provider result requires provider_name.")
    if not result.provider_reference:
        raise InvalidProviderResponseException("Provider result requires provider_reference.")
    if not result.provider_message:
        raise InvalidProviderResponseException("Provider result requires provider_message.")
    if not isinstance(result.timestamp, datetime):
        raise InvalidProviderResponseException("Provider result requires a timestamp.")
    try:
        ProviderResultStatus(result.status)
    except ValueError as exc:
        raise InvalidProviderResponseException(
            f"Unsupported provider result status '{result.status}'."
        ) from exc
    return result


def provider_result_from_response(response: ProviderResponse) -> ProviderResult:
    """Normalize a Task 1 ``ProviderResponse`` into a secret-free ``ProviderResult``."""

    metadata: Mapping[str, object] = response.metadata or {}
    status = str(metadata.get("status") or (
        ProviderResultStatus.SUCCESS if response.accepted else ProviderResultStatus.FAILURE
    ))
    message = str(metadata.get("provider_message") or (
        "accepted" if response.accepted else "rejected"
    ))
    reference = response.provider_reference or str(metadata.get("provider_reference") or "")
    raw_ts = metadata.get("timestamp")
    if isinstance(raw_ts, datetime):
        timestamp = raw_ts
    else:
        timestamp = datetime.now(timezone.utc)
    result = ProviderResult(
        status=status,
        provider_name=response.provider_name,
        provider_message=message,
        provider_reference=reference,
        timestamp=timestamp,
    )
    return validate_provider_result(result)
