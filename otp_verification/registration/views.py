"""HTTP views for registration OTP verification (lifecycle hardened)."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from otp_verification import constants
from otp_verification.enums import AuditEvent
from otp_verification.registration.completions import (
    AlreadyCompletedError,
    CompletionError,
    complete_pending_registration,
    mark_bureau_user_phone_verified,
    mark_expert_user_phone_verified,
    mark_pandit_user_phone_verified,
)
from otp_verification.registration.exceptions import (
    RegistrationOTPCooldownActive,
    RegistrationOTPDeliveryFailed,
    RegistrationOTPDisabled,
    RegistrationOTPError,
    RegistrationOTPExpired,
    RegistrationOTPGenerationLimitReached,
    RegistrationOTPInvalid,
    RegistrationOTPLocked,
    RegistrationOTPNotFound,
    RegistrationOTPRateLimited,
    RegistrationOTPReplay,
    RegistrationOTPResendLimitReached,
    RegistrationOTPServiceError,
    RegistrationOTPSessionExpired,
    RegistrationOTPValidationError,
)
from otp_verification.registration.adapters import normalize_destination
from otp_verification.registration.factory import (
    build_registration_otp_resend_service,
    build_registration_otp_service,
)
from otp_verification.registration.responses import (
    ERROR_COOLDOWN,
    ERROR_DELIVERY_FAILED,
    ERROR_DISABLED,
    ERROR_EXPIRED_CHALLENGE,
    ERROR_GENERATION_LIMIT,
    ERROR_INVALID_SESSION,
    ERROR_LOCKED_CHALLENGE,
    ERROR_OTP_FAILED,
    ERROR_OWNERSHIP,
    ERROR_PHONE_MISMATCH,
    ERROR_RATE_LIMITED,
    ERROR_REGISTRATION_FAILED,
    ERROR_REPLAY,
    ERROR_RESEND_LIMIT,
    ERROR_SESSION_EXPIRED,
    ERROR_UNEXPECTED,
    ERROR_VALIDATION,
    send_success_json,
    verification_error_json,
    verification_success_json,
)
from otp_verification.registration.session import (
    assert_otp_generation_available,
    clear_pending_registration,
    clear_phone_verified,
    cooldown_remaining_seconds,
    discard_empty_pending_bridge,
    finalize_registration_session,
    get_completed_registration,
    get_pending_registration,
    get_pending_resend_count,
    get_phone_challenge,
    is_registration_otp_verified,
    mark_registration_otp_verified,
    record_successful_otp_generation,
    store_phone_challenge,
    store_phone_verified,
)
from otp_verification.config import get_configuration

logger = logging.getLogger(__name__)


def _authenticated_user_phone(request) -> str | None:
    """Normalized phone for the logged-in user, or None if anonymous/unset."""

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    raw = str(getattr(user, "phone_number", "") or "").strip()
    if not raw:
        return None
    try:
        return normalize_destination(raw)
    except RegistrationOTPValidationError:
        return None


def _reject_if_authenticated_phone_mismatch(
    request,
    *,
    otp_phone: str,
    wants_json: bool = True,
):
    """Block OTP send/verify when logged-in user's phone != OTP destination.

    Returns an error response when mismatched; None when allowed.
    Anonymous / no-user-phone flows are unchanged (pre-registration).
    """

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    user_phone = _authenticated_user_phone(request)
    try:
        otp_normalized = normalize_destination(otp_phone)
    except RegistrationOTPValidationError:
        otp_normalized = ""

    if not user_phone:
        # Logged in but no stored phone — refuse binding OTP to an arbitrary number.
        logger.warning(
            "OTP blocked: authenticated user has no registered phone",
            extra={"user_id": getattr(user, "id", None)},
        )
        return verification_error_json(
            error=ERROR_PHONE_MISMATCH,
            message="Phone verification mismatch. Please use your registered number.",
            status=403,
        )

    if user_phone != otp_normalized:
        logger.warning(
            "OTP verification mismatch",
            extra={
                "user_id": getattr(user, "id", None),
                "user_phone": user_phone,
                "otp_phone": otp_normalized,
            },
        )
        if wants_json:
            return verification_error_json(
                error=ERROR_PHONE_MISMATCH,
                message="Phone verification mismatch. Please use your registered number.",
                status=403,
            )
        return _respond_error(
            request,
            wants_json=False,
            error=ERROR_PHONE_MISMATCH,
            message="Phone verification mismatch. Please use your registered number.",
            status=403,
        )
    return None


def _mark_authenticated_user_phone_verified(request, *, destination: str) -> bool:
    """Persist is_phone_verified when logged-in user's phone matches destination.

    Returns True when the user flag was updated (or already verified).
    Returns False on mismatch / anonymous — caller must not treat as verified.
    """

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    try:
        normalized = normalize_destination(destination)
        stored = normalize_destination(str(getattr(user, "phone_number", "") or ""))
    except RegistrationOTPValidationError:
        return False
    if not normalized or not stored or normalized != stored:
        logger.warning(
            "OTP verification mismatch",
            extra={
                "user_id": getattr(user, "id", None),
                "user_phone": stored or None,
                "otp_phone": normalized or destination,
            },
        )
        return False
    if getattr(user, "is_phone_verified", False):
        return True
    from django.utils import timezone

    user.is_phone_verified = True
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["is_phone_verified", "phone_verified_at", "updated_at"])
    return True


def _safe_reverse(name: str, fallback: str) -> str:
    try:
        return reverse(name)
    except Exception:  # noqa: BLE001 - tests without full URLconf
        return fallback


def _wants_json(request) -> bool:
    accept = ""
    if hasattr(request, "headers"):
        accept = request.headers.get("Accept") or ""
    return "application/json" in accept or "application/json" in (request.content_type or "")


def _verify_template_context(pending: dict) -> dict:
    config = get_configuration()
    resend_count = get_pending_resend_count(pending)
    max_resends = int(constants.MAX_OTP_GENERATIONS_PER_SESSION) - 1
    remaining_attempts = max(0, max_resends - resend_count)
    remaining_seconds = cooldown_remaining_seconds(
        pending,
        cooldown_seconds=int(config.resend_cooldown_seconds),
    )
    return {
        "challenge_id": str(pending.get("challenge_id") or ""),
        "flow_type": str(pending.get("flow_type") or ""),
        "resume_path": pending.get("resume_path")
        or _safe_reverse("accounts:register", "/accounts/register/"),
        "resend_url": _safe_reverse(
            "otp_verification:resend_registration_otp",
            "/otp/registration/resend/",
        ),
        "remaining_seconds": remaining_seconds,
        "remaining_attempts": remaining_attempts,
        "resend_enabled": remaining_seconds <= 0 and remaining_attempts > 0,
        "max_resends": max_resends,
        **_expert_skip_phone_verification_context(pending),
    }


def _expert_skip_phone_verification_context(pending: dict) -> dict:
    flow_type = str(pending.get("flow_type") or "")
    if flow_type == constants.FLOW_EXPERT_REGISTRATION:
        return {
            "allow_skip_phone_verification": True,
            "skip_phone_verification_url": _safe_reverse(
                "expert_register_skip_phone_otp",
                "/services/expert/register/skip-phone-otp/",
            ),
        }
    if flow_type == constants.FLOW_BUREAU_REGISTRATION:
        return {
            "allow_skip_phone_verification": True,
            "skip_phone_verification_url": _safe_reverse(
                "bureaus:bureau_register_skip_phone_otp",
                "/bureaus/register/skip-phone-otp/",
            ),
        }
    if flow_type == constants.FLOW_PANDIT_REGISTRATION:
        return {
            "allow_skip_phone_verification": True,
            "skip_phone_verification_url": _safe_reverse(
                "accounts:pandit_register_skip_phone_otp",
                "/accounts/pandit/register/skip-phone-otp/",
            ),
        }
    return {}


def _success_message(flow_type: str) -> str:
    if flow_type == constants.FLOW_PANDIT_REGISTRATION:
        return (
            "Registration successful. Please verify your email. Account awaits admin approval."
        )
    if flow_type == constants.FLOW_BUREAU_REGISTRATION:
        return "Registration successful. Awaiting admin approval."
    if flow_type == constants.FLOW_EXPERT_REGISTRATION:
        return "Registration successful. Your profile is pending approval."
    if flow_type == constants.FLOW_USER_REGISTRATION:
        return "Registration successful. Please verify your email, then log in."
    return "Registration successful."


def _success_redirect(flow_type: str, resume_path: str):
    if flow_type == constants.FLOW_USER_REGISTRATION:
        return redirect("accounts:login")
    if flow_type == constants.FLOW_EXPERT_REGISTRATION:
        return redirect("expert_pending")
    return redirect(resume_path)


def _respond_success(request, *, flow_type: str, resume_path: str, result, wants_json: bool):
    success_message = _success_message(flow_type)
    if wants_json:
        return verification_success_json(message=success_message, result=result)
    messages.success(request, success_message)
    return _success_redirect(flow_type, resume_path)


def _respond_error(
    request,
    *,
    wants_json: bool,
    error: str,
    message: str,
    status: int = 400,
    resume_path: str | None = None,
    clear_pending: bool = False,
    re_render: bool = False,
    challenge_id: str = "",
    flow_type: str = "",
):
    if clear_pending:
        clear_pending_registration(request)
    if wants_json:
        return verification_error_json(error=error, message=message, status=status)
    messages.error(request, message)
    if re_render:
        pending = None
        try:
            pending = get_pending_registration(request, enforce_ttl=False)
        except Exception:  # noqa: BLE001
            pending = None
        if pending:
            context = _verify_template_context(pending)
        else:
            context = {
                "challenge_id": challenge_id,
                "flow_type": flow_type,
                "resume_path": resume_path or reverse("accounts:register"),
                "resend_url": reverse("otp_verification:resend_registration_otp"),
                "remaining_seconds": 0,
                "remaining_attempts": 0,
                "resend_enabled": False,
                "max_resends": 0,
            }
        return render(
            request,
            "otp_verification/verify_registration_otp.html",
            context,
            status=status,
        )
    return redirect(resume_path or reverse("accounts:register"))


def _map_verify_failure(exc: Exception) -> tuple[str, str, bool]:
    """Return (error_code, message, clear_pending)."""

    if isinstance(exc, RegistrationOTPExpired):
        return (
            ERROR_EXPIRED_CHALLENGE,
            str(exc) or "OTP expired. Please request a new one.",
            True,
        )
    if isinstance(exc, RegistrationOTPLocked):
        return ERROR_LOCKED_CHALLENGE, str(exc) or "OTP challenge is locked.", True
    if isinstance(exc, RegistrationOTPReplay):
        return ERROR_REPLAY, str(exc) or "This OTP challenge can no longer be used.", True
    if isinstance(exc, RegistrationOTPNotFound):
        return ERROR_INVALID_SESSION, str(exc) or "OTP challenge not found.", True
    if isinstance(exc, RegistrationOTPInvalid):
        return ERROR_OTP_FAILED, str(exc) or "Invalid OTP code.", False
    if isinstance(exc, RegistrationOTPValidationError):
        return ERROR_VALIDATION, str(exc), False
    if isinstance(exc, RegistrationOTPSessionExpired):
        return ERROR_SESSION_EXPIRED, str(exc), True
    message = str(exc) or "OTP verification failed."
    return ERROR_OTP_FAILED, message, False


@require_http_methods(["GET", "POST"])
def verify_registration_otp(request):
    """Verify OTP for a paused registration and complete account creation."""

    wants_json = _wants_json(request)

    # Idempotent replay of an already-completed registration in this session.
    completed = get_completed_registration(request)
    if completed and request.method == "POST":
        posted_challenge = (request.POST.get("challenge_id") or "").strip()
        if posted_challenge and posted_challenge == str(completed.get("challenge_id") or ""):
            logger.info(
                "event=%s flow=%s challenge=%s mode=idempotent",
                AuditEvent.REGISTRATION_COMPLETED,
                completed.get("flow_type"),
                completed.get("challenge_id"),
            )
            return _respond_success(
                request,
                flow_type=completed.get("flow_type") or "",
                resume_path=reverse("accounts:register"),
                result=completed.get("result") or {},
                wants_json=wants_json,
            )

    try:
        pending = get_pending_registration(request, enforce_ttl=True)
    except RegistrationOTPSessionExpired as exc:
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_SESSION_EXPIRED,
            message=str(exc),
            clear_pending=False,  # already cleared by get_pending_registration
        )

    if not pending:
        phone_challenge = get_phone_challenge(request)
        if phone_challenge and request.method == "POST":
            return _verify_phone_challenge_only(
                request,
                phone_challenge=phone_challenge,
                wants_json=wants_json,
            )
        message = "No pending registration OTP found. Please register again."
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_INVALID_SESSION,
            message=message,
        )

    challenge_id = str(pending.get("challenge_id") or "")
    flow_type = str(pending.get("flow_type") or "")
    resume_path = pending.get("resume_path") or reverse("accounts:register")
    destination = str(pending.get("destination") or "").strip()

    if request.method == "GET":
        return render(
            request,
            "otp_verification/verify_registration_otp.html",
            _verify_template_context(pending),
        )

    submitted_otp = (request.POST.get("otp") or request.POST.get("submitted_otp") or "").strip()
    posted_challenge = (request.POST.get("challenge_id") or "").strip()

    logger.info(
        "event=%s flow=%s challenge=%s",
        AuditEvent.REGISTRATION_VERIFY_STARTED,
        flow_type,
        challenge_id,
    )

    # Do not trust Challenge ID alone — must match the session-owned pending challenge.
    if not posted_challenge or posted_challenge != challenge_id:
        message = "Invalid verification request. Please restart registration."
        logger.info(
            "event=%s flow=%s reason=ownership_failure",
            AuditEvent.REGISTRATION_VERIFY_FAILED,
            flow_type,
        )
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_OWNERSHIP,
            message=message,
            clear_pending=True,
            resume_path=resume_path,
        )

    service = build_registration_otp_service()

    try:
        # If OTP was already verified but completion failed, skip re-verify (replay-safe).
        if is_registration_otp_verified(
            request,
            flow_type=flow_type,
            challenge_id=challenge_id,
        ):
            verified_flow = flow_type
            verified_challenge = challenge_id
            logger.info(
                "event=%s flow=%s challenge=%s mode=resume_verified",
                AuditEvent.REGISTRATION_VERIFY_SUCCEEDED,
                verified_flow,
                verified_challenge,
            )
        else:
            if not submitted_otp:
                raise RegistrationOTPValidationError("OTP code is required.")
            verified = service.verify_challenge(
                challenge_id=posted_challenge,
                submitted_otp=submitted_otp,
            )
            if verified.flow_type != flow_type or verified.challenge_id != challenge_id:
                logger.info(
                    "event=%s flow=%s reason=flow_or_challenge_mismatch",
                    AuditEvent.REGISTRATION_VERIFY_FAILED,
                    flow_type,
                )
                return _respond_error(
                    request,
                    wants_json=wants_json,
                    error=ERROR_OWNERSHIP,
                    message="Invalid verification request. Please restart registration.",
                    clear_pending=True,
                    resume_path=resume_path,
                )
            mark_registration_otp_verified(
                request,
                challenge_id=verified.challenge_id,
                flow_type=verified.flow_type,
            )
            if destination:
                store_phone_verified(
                    request,
                    challenge_id=verified.challenge_id,
                    destination=destination,
                    flow_type=verified.flow_type,
                )
            verified_flow = verified.flow_type
            verified_challenge = verified.challenge_id
            logger.info(
                "event=%s flow=%s challenge=%s",
                AuditEvent.REGISTRATION_VERIFY_SUCCEEDED,
                verified_flow,
                verified_challenge,
            )

        # Registration resume → transactional create (inside completer) → finalize session.
        result = complete_pending_registration(pending=pending)
        if verified_flow == constants.FLOW_EXPERT_REGISTRATION:
            payload = pending.get("payload") or {}
            mark_expert_user_phone_verified(
                email=(result.get("email") or payload.get("email") or "").strip(),
                phone=(destination or payload.get("phone") or "").strip(),
            )
        elif verified_flow == constants.FLOW_BUREAU_REGISTRATION:
            payload = pending.get("payload") or {}
            mark_bureau_user_phone_verified(
                email=(result.get("email") or payload.get("email") or "").strip(),
                phone=(destination or payload.get("phone_number") or "").strip(),
            )
        elif verified_flow == constants.FLOW_PANDIT_REGISTRATION:
            payload = pending.get("payload") or {}
            mark_pandit_user_phone_verified(
                email=(result.get("email") or payload.get("email") or "").strip(),
                phone=(
                    destination
                    or payload.get("phone_number")
                    or payload.get("phone")
                    or ""
                ).strip(),
            )
        finalize_registration_session(
            request,
            challenge_id=verified_challenge,
            flow_type=verified_flow,
            result=result,
        )
        logger.info(
            "event=%s flow=%s challenge=%s",
            AuditEvent.REGISTRATION_COMPLETED,
            verified_flow,
            verified_challenge,
        )
        return _respond_success(
            request,
            flow_type=verified_flow,
            resume_path=resume_path,
            result=result,
            wants_json=wants_json,
        )
    except AlreadyCompletedError as exc:
        # Double-submit after create: treat as success, finalize session.
        result = getattr(exc, "result", {}) or {"flow_type": flow_type}
        finalize_registration_session(
            request,
            challenge_id=challenge_id,
            flow_type=flow_type,
            result=result,
        )
        logger.info(
            "event=%s flow=%s challenge=%s mode=already_completed",
            AuditEvent.REGISTRATION_COMPLETED,
            flow_type,
            challenge_id,
        )
        return _respond_success(
            request,
            flow_type=flow_type,
            resume_path=resume_path,
            result=result,
            wants_json=wants_json,
        )
    except (
        RegistrationOTPExpired,
        RegistrationOTPLocked,
        RegistrationOTPNotFound,
        RegistrationOTPReplay,
        RegistrationOTPInvalid,
        RegistrationOTPValidationError,
        RegistrationOTPError,
    ) as exc:
        error, message, should_clear = _map_verify_failure(exc)
        logger.info(
            "event=%s flow=%s challenge=%s error=%s",
            AuditEvent.REGISTRATION_VERIFY_FAILED,
            flow_type,
            challenge_id,
            error,
        )
        return _respond_error(
            request,
            wants_json=wants_json,
            error=error,
            message=message,
            clear_pending=should_clear,
            resume_path=resume_path,
            re_render=not should_clear,
            challenge_id=challenge_id,
            flow_type=flow_type,
        )
    except CompletionError as exc:
        # Keep verified marker + pending so completion can be retried without re-OTP.
        logger.info(
            "event=%s flow=%s challenge=%s error=registration_failed",
            AuditEvent.REGISTRATION_VERIFY_FAILED,
            flow_type,
            challenge_id,
        )
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_REGISTRATION_FAILED,
            message=str(exc),
            resume_path=resume_path,
            re_render=True,
            challenge_id=challenge_id,
            flow_type=flow_type,
        )
    except Exception:
        # Unexpected failure: keep pending so the user can retry; never leak internals.
        logger.exception(
            "event=%s flow=%s challenge=%s",
            AuditEvent.REGISTRATION_VERIFY_FAILED,
            flow_type,
            challenge_id,
        )
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_UNEXPECTED,
            message="Registration failed. Please try again.",
            status=500,
            resume_path=resume_path,
            re_render=True,
            challenge_id=challenge_id,
            flow_type=flow_type,
        )


def _verify_phone_challenge_only(request, *, phone_challenge: dict, wants_json: bool):
    """Verify OTP for pre-registration phone_challenge; store phone_verified only.

    Does not complete registration and does not create pending registration.
    Reuses RegistrationOTPService.verify_challenge unchanged.
    """

    challenge_id = str(phone_challenge.get("challenge_id") or "")
    flow_type = str(phone_challenge.get("flow_type") or "")
    destination = str(phone_challenge.get("destination") or "").strip()
    submitted_otp = (request.POST.get("otp") or request.POST.get("submitted_otp") or "").strip()
    posted_challenge = (request.POST.get("challenge_id") or "").strip()

    logger.info(
        "event=%s flow=%s challenge=%s mode=phone_challenge",
        AuditEvent.REGISTRATION_VERIFY_STARTED,
        flow_type,
        challenge_id,
    )

    if not posted_challenge or posted_challenge != challenge_id:
        logger.info(
            "event=%s flow=%s reason=ownership_failure",
            AuditEvent.REGISTRATION_VERIFY_FAILED,
            flow_type,
        )
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_OWNERSHIP,
            message="Invalid or expired OTP session.",
        )

    if not destination:
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_VALIDATION,
            message="Phone number is missing from the verification session.",
        )

    # CRITICAL: logged-in users may only verify OTP for their registered phone.
    mismatch = _reject_if_authenticated_phone_mismatch(
        request,
        otp_phone=destination,
        wants_json=wants_json,
    )
    if mismatch is not None:
        clear_phone_verified(request)
        return mismatch

    # Latest-challenge gate: posted id must match session (already checked above).
    try:
        if not submitted_otp:
            raise RegistrationOTPValidationError("OTP code is required.")
        verified = build_registration_otp_service().verify_challenge(
            challenge_id=posted_challenge,
            submitted_otp=submitted_otp,
        )
        if verified.flow_type != flow_type or verified.challenge_id != challenge_id:
            logger.info(
                "event=%s flow=%s reason=flow_or_challenge_mismatch",
                AuditEvent.REGISTRATION_VERIFY_FAILED,
                flow_type,
            )
            return _respond_error(
                request,
                wants_json=wants_json,
                error=ERROR_OWNERSHIP,
                message="Invalid or expired OTP session.",
            )

        user = getattr(request, "user", None)
        authenticated = bool(
            user is not None and getattr(user, "is_authenticated", False)
        )
        if authenticated:
            marked = _mark_authenticated_user_phone_verified(
                request, destination=destination
            )
            if not marked:
                clear_phone_verified(request)
                return _respond_error(
                    request,
                    wants_json=wants_json,
                    error=ERROR_PHONE_MISMATCH,
                    message="Phone verification mismatch. Please use your registered number.",
                    status=403,
                )

        store_phone_verified(
            request,
            challenge_id=verified.challenge_id,
            destination=destination,
            flow_type=verified.flow_type,
        )

        logger.info(
            "event=%s flow=%s challenge=%s mode=phone_verified",
            AuditEvent.REGISTRATION_VERIFY_SUCCEEDED,
            verified.flow_type,
            verified.challenge_id,
        )
        message = "Phone number verified."
        result = {
            "challenge_id": verified.challenge_id,
            "flow_type": verified.flow_type,
            "phone_verified": True,
        }
        if wants_json:
            return verification_success_json(message=message, result=result)
        messages.success(request, message)
        return redirect(_safe_reverse("accounts:register", "/accounts/register/"))
    except (
        RegistrationOTPExpired,
        RegistrationOTPLocked,
        RegistrationOTPNotFound,
        RegistrationOTPReplay,
        RegistrationOTPInvalid,
        RegistrationOTPValidationError,
        RegistrationOTPError,
    ) as exc:
        error, message, _should_clear = _map_verify_failure(exc)
        logger.info(
            "event=%s flow=%s challenge=%s error=%s",
            AuditEvent.REGISTRATION_VERIFY_FAILED,
            flow_type,
            challenge_id,
            error,
        )
        # Failures must not create or keep a stale phone_verified marker.
        # Keep phone_challenge session so expired OTP can be resent.
        clear_phone_verified(request)
        return _respond_error(
            request,
            wants_json=wants_json,
            error=error,
            message=message,
        )
    except Exception:
        logger.exception(
            "event=%s flow=%s challenge=%s",
            AuditEvent.REGISTRATION_VERIFY_FAILED,
            flow_type,
            challenge_id,
        )
        clear_phone_verified(request)
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_UNEXPECTED,
            message="Unable to verify OTP. Please try again.",
            status=500,
        )


@require_http_methods(["POST"])
def resend_registration_otp(request):
    """Resend OTP for a pending registration (Task 7B). CSRF required."""

    wants_json = _wants_json(request)
    posted_challenge = (request.POST.get("challenge_id") or "").strip()

    try:
        result = build_registration_otp_resend_service().resend(
            request,
            posted_challenge_id=posted_challenge,
        )
        message = "A new verification code has been sent."
        payload = {
            "challenge_id": result.challenge_id,
            "flow_type": result.flow_type,
            "status": result.status,
            "expires_at": result.expires_at.isoformat() if result.expires_at else None,
            "resend_count": result.resend_count,
            "remaining_attempts": result.remaining_attempts,
            "cooldown_seconds": result.cooldown_seconds,
            "remaining_seconds": result.cooldown_seconds,
            "resend_enabled": False,
        }
        if wants_json:
            return verification_success_json(
                message=message,
                result=payload,
                remaining_seconds=result.cooldown_seconds,
                remaining_attempts=result.remaining_attempts,
            )
        messages.success(request, message)
        pending = get_pending_registration(request, enforce_ttl=False)
        return render(
            request,
            "otp_verification/verify_registration_otp.html",
            _verify_template_context(pending or {"challenge_id": result.challenge_id}),
        )
    except RegistrationOTPCooldownActive as exc:
        if wants_json:
            return verification_error_json(
                error=ERROR_COOLDOWN,
                message=str(exc),
                status=429,
                remaining_seconds=exc.remaining_seconds,
            )
        messages.error(request, str(exc))
        pending = get_pending_registration(request, enforce_ttl=False)
        return render(
            request,
            "otp_verification/verify_registration_otp.html",
            _verify_template_context(pending) if pending else {"challenge_id": posted_challenge},
            status=429,
        )
    except RegistrationOTPGenerationLimitReached as exc:
        if wants_json:
            return verification_error_json(
                error=ERROR_GENERATION_LIMIT,
                message=str(exc),
                status=429,
                remaining_attempts=exc.remaining_attempts,
            )
        messages.error(request, str(exc))
        pending = get_pending_registration(request, enforce_ttl=False)
        return render(
            request,
            "otp_verification/verify_registration_otp.html",
            _verify_template_context(pending) if pending else {"challenge_id": posted_challenge},
            status=429,
        )
    except RegistrationOTPResendLimitReached as exc:
        if wants_json:
            return verification_error_json(
                error=ERROR_RESEND_LIMIT,
                message=str(exc),
                status=429,
                remaining_attempts=exc.remaining_attempts,
            )
        messages.error(request, str(exc))
        pending = get_pending_registration(request, enforce_ttl=False)
        return render(
            request,
            "otp_verification/verify_registration_otp.html",
            _verify_template_context(pending) if pending else {"challenge_id": posted_challenge},
            status=429,
        )
    except RegistrationOTPSessionExpired as exc:
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_SESSION_EXPIRED,
            message=str(exc),
        )
    except RegistrationOTPLocked as exc:
        clear_pending_registration(request)
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_LOCKED_CHALLENGE,
            message=str(exc),
            clear_pending=False,
        )
    except RegistrationOTPReplay as exc:
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_REPLAY,
            message=str(exc),
        )
    except RegistrationOTPDeliveryFailed as exc:
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_DELIVERY_FAILED,
            message=str(exc),
            re_render=True,
            challenge_id=posted_challenge,
        )
    except RegistrationOTPDisabled as exc:
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_INVALID_SESSION,
            message=str(exc),
        )
    except RegistrationOTPValidationError as exc:
        # Ownership / missing session — clear when ownership-like
        message = str(exc)
        is_ownership = "Invalid resend" in message or "restart registration" in message.lower()
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_OWNERSHIP if is_ownership else ERROR_VALIDATION,
            message=message,
            clear_pending=is_ownership,
            re_render=not is_ownership,
            challenge_id=posted_challenge,
        )
    except RegistrationOTPError as exc:
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_VALIDATION,
            message=str(exc),
            re_render=True,
            challenge_id=posted_challenge,
        )
    except Exception:
        logger.exception("event=%s", AuditEvent.RESEND_FAILED)
        return _respond_error(
            request,
            wants_json=wants_json,
            error=ERROR_UNEXPECTED,
            message="Unable to resend verification code. Please try again.",
            status=500,
            re_render=True,
            challenge_id=posted_challenge,
        )


def _read_send_fields(request) -> tuple[str, str]:
    """Extract phone_number + flow_type from form POST or JSON body."""

    phone = (request.POST.get("phone_number") or request.POST.get("phone") or "").strip()
    flow_type = (request.POST.get("flow_type") or "").strip()
    if phone and flow_type:
        return phone, flow_type
    content_type = (request.content_type or "").lower()
    if "application/json" in content_type and request.body:
        try:
            import json

            body = json.loads(request.body.decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError):
            return phone, flow_type
        if isinstance(body, dict):
            if not phone:
                phone = str(body.get("phone_number") or body.get("phone") or "").strip()
            if not flow_type:
                flow_type = str(body.get("flow_type") or "").strip()
    return phone, flow_type


@require_http_methods(["POST"])
def send_registration_otp(request):
    """Lightweight JSON adapter for registration OTP send.

    First matching request: RegistrationOTPService.start_verification().
    Subsequent matching requests: existing RegistrationOTPResendService policy
    (cooldown, limits, ownership, eligibility) via phone_challenge session.
    Does not create pending registration. No registration completion.
    """

    phone_number, flow_type = _read_send_fields(request)
    if not phone_number:
        return verification_error_json(
            error=ERROR_VALIDATION,
            message="Phone number is required for OTP verification.",
            status=400,
        )
    if not flow_type:
        return verification_error_json(
            error=ERROR_VALIDATION,
            message="flow_type is required.",
            status=400,
        )
    # Distinguish unknown flow (400) from OTP disabled for a known flow (403).
    if flow_type not in constants.FLOW_CHOICES:
        return verification_error_json(
            error=ERROR_VALIDATION,
            message=f"Unsupported OTP flow '{flow_type}'.",
            status=400,
        )

    try:
        normalized_phone = normalize_destination(phone_number)
    except RegistrationOTPValidationError as exc:
        return verification_error_json(
            error=ERROR_VALIDATION,
            message=str(exc) or "Invalid OTP request.",
            status=400,
        )

    # Logged-in users may only request OTP for their registered number.
    mismatch = _reject_if_authenticated_phone_mismatch(
        request,
        otp_phone=normalized_phone,
        wants_json=True,
    )
    if mismatch is not None:
        return mismatch

    phone_challenge = get_phone_challenge(request)
    reuse_resend = False
    if phone_challenge:
        try:
            challenge_dest = normalize_destination(
                str(phone_challenge.get("destination") or "")
            )
        except RegistrationOTPValidationError:
            challenge_dest = ""
        reuse_resend = (
            str(phone_challenge.get("flow_type") or "") == flow_type
            and challenge_dest == normalized_phone
            and bool(phone_challenge.get("challenge_id"))
        )

    if reuse_resend:
        # Existing challenge + cooldown/resend policy (blocks OTP spam).
        logger.info(
            "OTP send reused existing challenge (spam/cooldown path)",
            extra={
                "flow_type": flow_type,
                "challenge_id": phone_challenge.get("challenge_id"),
            },
        )
        return _send_via_existing_resend_policy(
            request,
            phone_challenge=phone_challenge,
            flow_type=flow_type,
            destination=normalized_phone,
        )

    return _send_initial_verification(
        request,
        flow_type=flow_type,
        destination=normalized_phone,
    )


def _send_initial_verification(request, *, flow_type: str, destination: str):
    """First Verify Mobile click: issue a new challenge via start_verification."""

    try:
        discard_empty_pending_bridge(request)
        assert_otp_generation_available(request, flow_type=flow_type)
        service = build_registration_otp_service()
        issued = service.start_verification(
            flow_type=flow_type,
            destination=destination,
        )
        record_successful_otp_generation(request, flow_type=flow_type)
        config = get_configuration()
        cooldown_remaining = int(config.resend_cooldown_seconds)
        store_phone_challenge(
            request,
            challenge_id=issued.challenge_id,
            flow_type=issued.flow_type,
            destination=destination,
            resend_count=0,
        )
        logger.info(
            "event=%s flow=%s challenge=%s",
            AuditEvent.OTP_SENT,
            issued.flow_type,
            issued.challenge_id,
        )
        expires_at = issued.expires_at.isoformat() if issued.expires_at else None
        return send_success_json(
            message="Verification code sent.",
            challenge_id=issued.challenge_id,
            flow_type=issued.flow_type,
            expires_at=expires_at,
            cooldown_remaining=cooldown_remaining,
        )
    except RegistrationOTPGenerationLimitReached as exc:
        return verification_error_json(
            error=ERROR_GENERATION_LIMIT,
            message=str(exc),
            status=429,
            remaining_attempts=exc.remaining_attempts,
        )
    except RegistrationOTPDisabled as exc:
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_DISABLED,
            message=str(exc) or "SMS OTP verification is not enabled.",
            status=403,
        )
    except RegistrationOTPValidationError as exc:
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_VALIDATION,
            message=str(exc) or "Invalid OTP request.",
            status=400,
        )
    except RegistrationOTPRateLimited as exc:
        logger.warning(
            "OTP spam/rate limit blocked",
            extra={"flow_type": flow_type},
        )
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_RATE_LIMITED,
            message=str(exc) or "Please wait before requesting a new OTP.",
            status=429,
        )
    except RegistrationOTPDeliveryFailed as exc:
        logger.warning(
            "SMS delivery failed (registration/account unaffected)",
            extra={"flow_type": flow_type, "error": str(exc)},
        )
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_DELIVERY_FAILED,
            message=str(exc) or "Unable to send OTP. Please try again.",
            status=502,
        )
    except RegistrationOTPServiceError as exc:
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_UNEXPECTED,
            message=str(exc) or "OTP verification is temporarily unavailable.",
            status=503,
        )
    except RegistrationOTPError as exc:
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_VALIDATION,
            message=str(exc) or "Unable to send verification code.",
            status=400,
        )
    except Exception:
        logger.exception("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_UNEXPECTED,
            message="Unable to send verification code. Please try again.",
            status=500,
        )


def _send_via_existing_resend_policy(
    request,
    *,
    phone_challenge: dict,
    flow_type: str,
    destination: str,
):
    """Repeat Verify Mobile click: reuse RegistrationOTPResendService policy."""

    challenge_id = str(phone_challenge.get("challenge_id") or "")
    try:
        discard_empty_pending_bridge(request)
        result = build_registration_otp_resend_service().resend(
            request,
            posted_challenge_id=challenge_id,
        )
        expires_at = result.expires_at.isoformat() if result.expires_at else None
        return send_success_json(
            message="Verification code sent.",
            challenge_id=result.challenge_id,
            flow_type=result.flow_type,
            expires_at=expires_at,
            cooldown_remaining=int(result.cooldown_seconds),
        )
    except RegistrationOTPCooldownActive as exc:
        logger.warning(
            "OTP spam blocked by cooldown",
            extra={"flow_type": flow_type, "remaining_seconds": exc.remaining_seconds},
        )
        return verification_error_json(
            error=ERROR_COOLDOWN,
            message=str(exc) or "Please wait before requesting a new OTP.",
            status=429,
            remaining_seconds=exc.remaining_seconds,
        )
    except RegistrationOTPGenerationLimitReached as exc:
        return verification_error_json(
            error=ERROR_GENERATION_LIMIT,
            message=str(exc),
            status=429,
            remaining_attempts=exc.remaining_attempts,
        )
    except RegistrationOTPResendLimitReached as exc:
        return verification_error_json(
            error=ERROR_RESEND_LIMIT,
            message=str(exc),
            status=429,
            remaining_attempts=exc.remaining_attempts,
        )
    except RegistrationOTPDisabled as exc:
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_DISABLED,
            message=str(exc) or "SMS OTP verification is not enabled.",
            status=403,
        )
    except RegistrationOTPLocked as exc:
        return verification_error_json(
            error=ERROR_LOCKED_CHALLENGE,
            message=str(exc) or "OTP challenge is locked.",
            status=400,
        )
    except RegistrationOTPReplay as exc:
        return verification_error_json(
            error=ERROR_REPLAY,
            message=str(exc) or "This OTP challenge can no longer be used.",
            status=400,
        )
    except RegistrationOTPSessionExpired as exc:
        return verification_error_json(
            error=ERROR_SESSION_EXPIRED,
            message=str(exc),
            status=400,
        )
    except RegistrationOTPDeliveryFailed as exc:
        logger.warning(
            "SMS delivery failed on resend (account unaffected)",
            extra={"flow_type": flow_type, "error": str(exc)},
        )
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_DELIVERY_FAILED,
            message=str(exc) or "Unable to send OTP. Please try again.",
            status=502,
        )
    except RegistrationOTPValidationError as exc:
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        message = str(exc)
        is_ownership = "Invalid resend" in message or "restart registration" in message.lower()
        return verification_error_json(
            error=ERROR_OWNERSHIP if is_ownership else ERROR_VALIDATION,
            message=message or "Invalid OTP request.",
            status=400,
        )
    except RegistrationOTPError as exc:
        logger.info("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_VALIDATION,
            message=str(exc) or "Unable to send verification code.",
            status=400,
        )
    except Exception:
        logger.exception("event=%s flow=%s", AuditEvent.OTP_SEND_FAILED, flow_type)
        return verification_error_json(
            error=ERROR_UNEXPECTED,
            message="Unable to send verification code. Please try again.",
            status=500,
        )
