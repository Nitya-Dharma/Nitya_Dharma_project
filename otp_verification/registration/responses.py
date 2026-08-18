"""Standardized verification HTTP JSON responses (registration-safe)."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Stable error codes for clients. Messages stay human-readable and secret-free.
ERROR_VALIDATION = "validation_error"
ERROR_EXPIRED_CHALLENGE = "expired_challenge"
ERROR_LOCKED_CHALLENGE = "locked_challenge"
ERROR_REPLAY = "replay"
ERROR_OWNERSHIP = "ownership_failure"
ERROR_SESSION_EXPIRED = "session_expired"
ERROR_INVALID_SESSION = "invalid_session"
ERROR_REGISTRATION_FAILED = "registration_failed"
ERROR_UNEXPECTED = "unexpected_failure"
ERROR_OTP_FAILED = "otp_verification_failed"  # generic wrong-OTP (backward compatible)
ERROR_COOLDOWN = "cooldown_active"
ERROR_RESEND_LIMIT = "resend_limit_reached"
ERROR_GENERATION_LIMIT = "otp_generation_limit_reached"
ERROR_DELIVERY_FAILED = "otp_delivery_failed"
ERROR_DISABLED = "otp_disabled"
ERROR_RATE_LIMITED = "rate_limited"
ERROR_PHONE_MISMATCH = "phone_mismatch"


def _log_envelope(kind: str, payload: Mapping[str, Any]) -> None:
    """Debug-only confirmation that old + new schema keys coexist."""

    logger.debug(
        "otp_api_envelope kind=%s status=%s has_result=%s has_error=%s "
        "has_error_code=%s has_challenge_id=%s keys=%s",
        kind,
        payload.get("status"),
        "result" in payload,
        "error" in payload,
        "error_code" in payload,
        "challenge_id" in payload,
        sorted(payload.keys()),
    )


def verification_success_json(
    *,
    message: str,
    result: Mapping[str, Any] | None = None,
    status: int = 200,
    remaining_seconds: int | None = None,
    remaining_attempts: int | None = None,
) -> JsonResponse:
    payload: dict[str, Any] = {
        "status": "success",
        "message": message,
        "result": dict(result or {}),
        "error_code": None,
    }
    if remaining_seconds is not None:
        payload["remaining_seconds"] = remaining_seconds
    if remaining_attempts is not None:
        payload["remaining_attempts"] = remaining_attempts
    _log_envelope("verification_success", payload)
    return JsonResponse(payload, status=status)


def verification_error_json(
    *,
    error: str,
    message: str,
    status: int = 400,
    remaining_seconds: int | None = None,
    remaining_attempts: int | None = None,
) -> JsonResponse:
    """Consistent error envelope. Never include provider/transport/exception dumps."""

    payload: dict[str, Any] = {
        "status": "error",
        "error": error,
        "error_code": error,
        "result": None,
        "message": message,
    }
    if remaining_seconds is not None:
        payload["remaining_seconds"] = remaining_seconds
    if remaining_attempts is not None:
        payload["remaining_attempts"] = remaining_attempts
    _log_envelope("verification_error", payload)
    return JsonResponse(payload, status=status)


def send_success_json(
    *,
    message: str,
    challenge_id: str,
    flow_type: str,
    expires_at: str | None,
    cooldown_remaining: int,
    status: int = 200,
) -> JsonResponse:
    """Safe JSON envelope for lightweight registration OTP send (no secrets).

    Keeps legacy flat fields and adds nested ``result`` + ``error_code`` for
    forward-compatible clients.
    """

    cooldown = max(0, int(cooldown_remaining))
    payload: dict[str, Any] = {
        "status": "success",
        "message": message,
        "challenge_id": challenge_id,
        "flow_type": flow_type,
        "expires_at": expires_at,
        "cooldown_remaining": cooldown,
        "result": {
            "challenge_id": challenge_id,
            "flow_type": flow_type,
            "expires_at": expires_at,
            "cooldown_remaining": cooldown,
        },
        "error_code": None,
    }
    _log_envelope("send_success", payload)
    return JsonResponse(payload, status=status)
