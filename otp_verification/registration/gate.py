"""Shared OTP gate used by registration views (feature-flagged)."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from otp_verification.enums import AuditEvent, ChallengeStatus
from otp_verification import constants
from otp_verification.registration.exceptions import (
    RegistrationOTPError,
    RegistrationOTPGenerationLimitReached,
    RegistrationOTPNotFound,
)
from otp_verification.registration.factory import (
    build_registration_otp_service,
    is_registration_otp_required,
)
from otp_verification.registration.responses import ERROR_GENERATION_LIMIT
from otp_verification.registration.session import (
    PENDING_SESSION_KEY,
    assert_otp_generation_available,
    is_registration_otp_verified,
    phone_verified_matches_registration,
    record_successful_otp_generation,
    store_pending_registration,
)

logger = logging.getLogger(__name__)


def _challenge_represents_successful_verification(
    *,
    challenge_id: str,
    flow_type: str,
) -> bool:
    """True when the bound challenge is still in a verified state for this flow."""

    try:
        status = build_registration_otp_service().get_challenge_status(
            challenge_id=challenge_id,
        )
    except RegistrationOTPNotFound:
        return False
    except RegistrationOTPError:
        return False
    except Exception:  # noqa: BLE001 - fall back to OTP rather than skip insecurely
        return False

    if str(status.flow_type or "") != str(flow_type):
        return False
    raw_status = getattr(status.status, "value", status.status)
    return str(raw_status) == ChallengeStatus.VERIFIED.value


def begin_otp_or_continue(
    request,
    *,
    flow_type: str,
    destination: str | None,
    payload: Mapping[str, Any],
    resume_path: str,
    wants_json: bool = False,
) -> HttpResponse | None:
    """Start OTP when required; return an HTTP response to pause registration.

    Returns None when:
    - OTP is disabled (caller uses existing create logic), or
    - a valid phone_verified session matches this flow + phone (skip OTP issue only).

    When OTP was already verified but completion is unfinished, redirects
    to the verify endpoint so completion uses the session pending payload
    (never fresh POST fields).
    """

    if not is_registration_otp_required(flow_type):
        return None

    pending_challenge = None
    pending = request.session.get(PENDING_SESSION_KEY)
    if isinstance(pending, dict):
        pending_challenge = pending.get("challenge_id")

    if is_registration_otp_verified(
        request,
        flow_type=flow_type,
        challenge_id=pending_challenge,
    ):
        # Do not fall through to legacy registration create with request.POST.
        verify_url = reverse("otp_verification:verify_registration_otp")
        message = "Complete OTP verification to finish registration."
        if wants_json:
            return JsonResponse(
                {
                    "status": "otp_verified_pending_completion",
                    "message": message,
                    "verify_url": verify_url,
                    "challenge_id": pending_challenge,
                    "flow_type": flow_type,
                    "result": {
                        "verify_url": verify_url,
                        "challenge_id": pending_challenge,
                        "flow_type": flow_type,
                    },
                    "error_code": None,
                },
                status=202,
            )
        messages.info(request, message)
        return redirect(verify_url)

    # Pre-verified phone: skip OTP issuance only; caller continues existing create.
    phone_verified = phone_verified_matches_registration(
        request,
        flow_type=flow_type,
        destination=destination,
    )
    if phone_verified is not None:
        challenge_id = str(phone_verified.get("challenge_id") or "")
        if _challenge_represents_successful_verification(
            challenge_id=challenge_id,
            flow_type=flow_type,
        ):
            logger.info(
                "event=%s flow=%s challenge=%s mode=phone_verified_skip_otp",
                AuditEvent.REGISTRATION_VERIFY_SUCCEEDED,
                flow_type,
                challenge_id,
            )
            return None
        logger.info(
            "event=%s flow=%s challenge=%s reason=phone_verified_challenge_invalid",
            AuditEvent.REGISTRATION_VERIFY_FAILED,
            flow_type,
            challenge_id,
        )

    if not destination:
        message = "Phone number is required for SMS verification."
        if wants_json:
            return JsonResponse(
                {
                    "status": "error",
                    "error": "phone_required",
                    "error_code": "phone_required",
                    "result": None,
                    "message": message,
                },
                status=400,
            )
        messages.error(request, message)
        return HttpResponse(status=400)

    try:
        assert_otp_generation_available(request, flow_type=flow_type)
        service = build_registration_otp_service()
        issued = service.start_verification(
            flow_type=flow_type,
            destination=destination,
            context={
                "resume_path": resume_path,
                "email": payload.get("email"),
            },
        )
        record_successful_otp_generation(request, flow_type=flow_type)
    except RegistrationOTPGenerationLimitReached as exc:
        if wants_json:
            return JsonResponse(
                {
                    "status": "error",
                    "error": ERROR_GENERATION_LIMIT,
                    "error_code": ERROR_GENERATION_LIMIT,
                    "result": None,
                    "message": str(exc),
                    "remaining_attempts": exc.remaining_attempts,
                },
                status=429,
            )
        messages.error(request, str(exc))
        return HttpResponse(status=429)
    except RegistrationOTPError as exc:
        if wants_json:
            return JsonResponse(
                {
                    "status": "error",
                    "error": "otp_delivery_failed",
                    "error_code": "otp_delivery_failed",
                    "result": None,
                    "message": str(exc),
                },
                status=400,
            )
        messages.error(request, str(exc))
        # Must not fall through to account creation when OTP is required.
        return HttpResponse(status=400)

    store_pending_registration(
        request,
        flow_type=flow_type,
        challenge_id=issued.challenge_id,
        destination=destination,
        payload=payload,
        resume_path=resume_path,
    )

    verify_url = reverse("otp_verification:verify_registration_otp")
    context = {
        "challenge_id": issued.challenge_id,
        "flow_type": flow_type,
        "expires_at": issued.expires_at,
        "resume_path": resume_path,
        "verify_url": verify_url,
    }
    if flow_type == constants.FLOW_EXPERT_REGISTRATION:
        context["allow_skip_phone_verification"] = True
        context["skip_phone_verification_url"] = reverse(
            "expert_register_skip_phone_otp"
        )
    if wants_json:
        return JsonResponse(
            {
                "status": "otp_required",
                "message": "Enter the OTP sent to your phone to continue registration.",
                "challenge_id": issued.challenge_id,
                "flow_type": flow_type,
                "verify_url": verify_url,
                "result": {
                    "challenge_id": issued.challenge_id,
                    "flow_type": flow_type,
                    "verify_url": verify_url,
                },
                "error_code": None,
            },
            status=202,
        )
    messages.info(request, "Enter the OTP sent to your phone to continue registration.")
    return render(request, "otp_verification/verify_registration_otp.html", context)
