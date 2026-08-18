"""Adapters mapping engine/orchestration results to registration-safe DTOs."""

from __future__ import annotations

import logging
from typing import Mapping

from otp_verification import constants
from otp_verification.domain.challenge import ChallengeView
from otp_verification.exceptions import (
    ChallengeExpiredException,
    ChallengeLockedException,
    ChallengeNotFoundException,
    InvalidOTPException,
    InvalidPhoneException,
    OTPException,
    ProviderException,
    RateLimitException,
    ReplayAttackException,
    RepositoryUnavailableException,
    ValidationException,
)
from otp_verification.registration.contracts import (
    RegistrationOTPIssueResult,
    RegistrationOTPStatusResult,
    RegistrationOTPVerifyResult,
)
from otp_verification.registration.exceptions import (
    RegistrationOTPDeliveryFailed,
    RegistrationOTPExpired,
    RegistrationOTPInvalid,
    RegistrationOTPLocked,
    RegistrationOTPNotFound,
    RegistrationOTPRateLimited,
    RegistrationOTPReplay,
    RegistrationOTPServiceError,
    RegistrationOTPValidationError,
)
from otp_verification.services.orchestration import ProviderDeliveryResult
from otp_verification.validators import validate_enabled_flow

logger = logging.getLogger(__name__)


def normalize_phone_number(phone: str) -> str | None:
    """Normalize Indian mobile numbers to 91XXXXXXXXXX for OTP delivery."""

    phone = str(phone or "").strip()
    phone = "".join(filter(str.isdigit, phone))

    if phone.startswith("91") and len(phone) == 12:
        return phone
    if len(phone) == 10:
        return "91" + phone
    return None


def normalize_destination(destination: str) -> str:
    """Light destination normalization for registration callers (not MSG91-specific)."""

    if destination is None or not str(destination).strip():
        raise RegistrationOTPValidationError("Phone number is required for OTP verification.")

    original = str(destination).strip()
    normalized = normalize_phone_number(original)
    if normalized is None:
        raise RegistrationOTPValidationError("Phone number format is invalid.")

    logger.info(
        "Normalized phone number",
        extra={"original": original, "normalized": normalized},
    )
    return normalized


def adapt_issue_request(
    *,
    flow_type: str,
    destination: str,
    context: Mapping[str, object] | None,
) -> tuple[str, str, dict[str, object]]:
    """Validate and map registration inputs into engine/orchestrator arguments."""

    try:
        validated_flow = validate_enabled_flow(flow_type)
    except Exception as exc:  # ConfigurationException
        raise RegistrationOTPValidationError(str(exc)) from exc

    phone = normalize_destination(destination)
    safe_context: dict[str, object] = {
        constants.CONTEXT_FLOW_TYPE: validated_flow,
        constants.CONTEXT_CANONICAL_PHONE: phone,
    }
    if context:
        # Never allow callers to inject plaintext OTP keys.
        for key, value in context.items():
            if key in {"otp", "otp_code", "otp_hash", "plaintext_otp", "message"}:
                continue
            safe_context[key] = value
    return validated_flow, phone, safe_context


def adapt_issue_result(delivery: ProviderDeliveryResult) -> RegistrationOTPIssueResult:
    """Map delivery result to a registration-safe DTO (strip provider details)."""

    challenge = delivery.challenge
    return RegistrationOTPIssueResult(
        challenge_id=challenge.id,
        flow_type=challenge.flow_type,
        status=challenge.status,
        expires_at=challenge.expires_at,
        attempt_count=challenge.attempt_count,
        max_attempts=challenge.max_attempts,
    )


def adapt_verify_result(challenge: ChallengeView) -> RegistrationOTPVerifyResult:
    return RegistrationOTPVerifyResult(
        challenge_id=challenge.id,
        flow_type=challenge.flow_type,
        status=challenge.status,
        verified_at=challenge.verified_at,
        expires_at=challenge.expires_at,
    )


def adapt_status_result(challenge: ChallengeView) -> RegistrationOTPStatusResult:
    return RegistrationOTPStatusResult(
        challenge_id=challenge.id,
        flow_type=challenge.flow_type,
        status=challenge.status,
        expires_at=challenge.expires_at,
        attempt_count=challenge.attempt_count,
        max_attempts=challenge.max_attempts,
        verified_at=challenge.verified_at,
    )


def map_exception(exc: Exception) -> Exception:
    """Translate engine/provider exceptions into registration-friendly errors."""

    if isinstance(exc, (RegistrationOTPValidationError, InvalidPhoneException, ValidationException)):
        return RegistrationOTPValidationError(str(exc) or "Invalid OTP request.")
    if isinstance(exc, ChallengeExpiredException):
        return RegistrationOTPExpired("OTP challenge has expired. Please request a new code.")
    if isinstance(exc, ChallengeLockedException):
        return RegistrationOTPLocked("Too many incorrect attempts. OTP verification is locked.")
    if isinstance(exc, InvalidOTPException):
        return RegistrationOTPInvalid("The OTP you entered is incorrect.")
    if isinstance(exc, ChallengeNotFoundException):
        return RegistrationOTPNotFound("OTP challenge was not found.")
    if isinstance(exc, RateLimitException):
        return RegistrationOTPRateLimited("Too many requests. Please try again later.")
    if isinstance(exc, ReplayAttackException):
        return RegistrationOTPReplay("This OTP challenge can no longer be used.")
    if isinstance(exc, RepositoryUnavailableException):
        return RegistrationOTPServiceError(
            "OTP verification is temporarily unavailable. Please try again later."
        )
    if isinstance(exc, ProviderException):
        return RegistrationOTPDeliveryFailed(
            "Unable to send verification code. Please try again later."
        )
    if isinstance(exc, OTPException):
        return RegistrationOTPServiceError(
            "OTP verification is temporarily unavailable. Please try again later."
        )
    return RegistrationOTPServiceError(
        "OTP verification is temporarily unavailable. Please try again later."
    )
