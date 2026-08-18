"""Session helpers for paused registration awaiting OTP verification."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from django.contrib.auth.hashers import make_password

from otp_verification import constants
from otp_verification.config import get_configuration
from otp_verification.enums import AuditEvent
from otp_verification.registration.exceptions import (
    RegistrationOTPGenerationLimitReached,
    RegistrationOTPSessionExpired,
)

logger = logging.getLogger(__name__)

PENDING_SESSION_KEY = "otp.registration.pending"
VERIFIED_SESSION_KEY = "otp.registration.verified"
COMPLETED_SESSION_KEY = "otp.registration.completed"
# Legacy send-only hint (superseded by phone_challenge for pre-registration send).
PRE_SEND_SESSION_KEY = "otp.registration.pre_send"
# Pre-registration phone verification only — never holds registration payload.
PHONE_CHALLENGE_SESSION_KEY = "otp.registration.phone_challenge"
# Temporary proof that a phone was verified for a flow (not consumed by registration yet).
PHONE_VERIFIED_SESSION_KEY = "otp.registration.phone_verified"
# Independent successful-generation budget. It intentionally survives pending/challenge
# replacement and is never keyed by referral data.
GENERATION_BUDGET_SESSION_KEY = "otp.registration.generation_budget"

# Minimal allowlists — only fields required to complete registration after OTP.
_FLOW_PAYLOAD_ALLOWLIST: dict[str, frozenset[str]] = {
    constants.FLOW_USER_REGISTRATION: frozenset(
        {"email", "password", "first_name", "last_name", "phone", "phone_number"}
    ),
    constants.FLOW_BUREAU_REGISTRATION: frozenset(
        {
            "bureau_name",
            "email",
            "password",
            "phone_number",
            "address",
            "city",
            "whatsapp_number",
        }
    ),
    constants.FLOW_EXPERT_REGISTRATION: frozenset(
        {
            "name",
            "email",
            "password",
            "phone",
            "experience_years",
            "description",
            "expert_type",
            "service_slugs",
            "social_links",
        }
    ),
    constants.FLOW_PANDIT_REGISTRATION: frozenset(
        {
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "phone_number",
            "referral_link_id",
            "referral_code",
        }
    ),
}

_MAX_DESCRIPTION_LEN = 500
_MAX_ADDRESS_LEN = 500
_MAX_SOCIAL_LINKS = 5
_MAX_SOCIAL_LINK_LEN = 200
_MAX_EXPERT_SERVICES = 3
_MAX_SERVICE_SLUG_LEN = 50
_MAX_TEXT_LEN = 255


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: object) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def minimize_registration_payload(
    *,
    flow_type: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep only allowlisted, size-capped fields required for completion."""

    allowed = _FLOW_PAYLOAD_ALLOWLIST.get(flow_type, frozenset())
    raw = {k: v for k, v in dict(payload).items() if k in allowed}

    if "password" in raw and raw["password"]:
        raw["password_hash"] = make_password(str(raw.pop("password")))
    else:
        raw.pop("password", None)
    raw.pop("password_confirm", None)
    raw.pop("confirm_password", None)

    for key in ("email", "first_name", "last_name", "name", "bureau_name", "city", "expert_type"):
        if key in raw and raw[key] is not None:
            raw[key] = str(raw[key]).strip()[:_MAX_TEXT_LEN]

    for key in ("phone", "phone_number", "whatsapp_number", "referral_code"):
        if key in raw and raw[key] is not None:
            raw[key] = str(raw[key]).strip()[:32]

    if "address" in raw and raw["address"] is not None:
        raw["address"] = str(raw["address"]).strip()[:_MAX_ADDRESS_LEN]

    if "description" in raw and raw["description"] is not None:
        raw["description"] = str(raw["description"]).strip()[:_MAX_DESCRIPTION_LEN]

    if "social_links" in raw:
        links = raw.get("social_links") or []
        if not isinstance(links, list):
            links = []
        cleaned: list[str] = []
        for link in links[:_MAX_SOCIAL_LINKS]:
            text = str(link).strip()[:_MAX_SOCIAL_LINK_LEN]
            if text:
                cleaned.append(text)
        raw["social_links"] = cleaned

    if "service_slugs" in raw:
        slugs = raw.get("service_slugs") or []
        if not isinstance(slugs, list):
            slugs = []
        cleaned_slugs: list[str] = []
        for slug in slugs[:_MAX_EXPERT_SERVICES]:
            text = str(slug).strip().lower()[:_MAX_SERVICE_SLUG_LEN]
            if text and text not in cleaned_slugs:
                cleaned_slugs.append(text)
        raw["service_slugs"] = cleaned_slugs

    if "experience_years" in raw:
        try:
            raw["experience_years"] = max(0, int(raw["experience_years"]))
        except (TypeError, ValueError):
            raw["experience_years"] = 0

    if "referral_link_id" in raw and raw["referral_link_id"] is not None:
        try:
            raw["referral_link_id"] = int(raw["referral_link_id"])
        except (TypeError, ValueError):
            raw.pop("referral_link_id", None)

    return raw


def store_pre_send_challenge(
    request,
    *,
    challenge_id: str,
    flow_type: str,
    destination: str,
) -> None:
    """Store only send-OTP ownership hints. Never stores registration payload.

    Deprecated for new send-path code — prefer ``store_phone_challenge``.
    """

    request.session[PRE_SEND_SESSION_KEY] = {
        "challenge_id": str(challenge_id),
        "flow_type": str(flow_type),
        "destination": str(destination).strip()[:32],
        "created_at": _utcnow().isoformat(),
    }
    request.session.modified = True


def get_pre_send_challenge(request) -> dict[str, Any] | None:
    """Return send-only session hint or None."""

    data = request.session.get(PRE_SEND_SESSION_KEY)
    if not isinstance(data, dict):
        return None
    if not data.get("challenge_id") or not data.get("flow_type"):
        return None
    return data


def store_phone_challenge(
    request,
    *,
    challenge_id: str,
    flow_type: str,
    destination: str,
    resend_count: int = 0,
    last_resent_at: str | None = None,
    created_at: str | None = None,
) -> None:
    """Store pre-registration phone OTP challenge state (no registration payload)."""

    now = _utcnow().isoformat()
    request.session[PHONE_CHALLENGE_SESSION_KEY] = {
        "challenge_id": str(challenge_id),
        "flow_type": str(flow_type),
        "destination": str(destination).strip()[:32],
        "created_at": created_at or now,
        "last_resent_at": last_resent_at or created_at or now,
        "resend_count": max(0, int(resend_count)),
    }
    # Phone-challenge owns pre-registration send state; drop legacy hint if present.
    request.session.pop(PRE_SEND_SESSION_KEY, None)
    # New challenge invalidates any prior phone-verified proof.
    request.session.pop(PHONE_VERIFIED_SESSION_KEY, None)
    request.session.modified = True


def get_phone_challenge(request) -> dict[str, Any] | None:
    """Return phone-challenge session or None."""

    data = request.session.get(PHONE_CHALLENGE_SESSION_KEY)
    if not isinstance(data, dict):
        return None
    if not data.get("challenge_id") or not data.get("flow_type"):
        return None
    return data


def clear_phone_challenge(request) -> None:
    """Clear pre-registration phone-challenge session only."""

    request.session.pop(PHONE_CHALLENGE_SESSION_KEY, None)
    request.session.modified = True


def discard_empty_pending_bridge(request) -> None:
    """Remove leftover empty-payload pending bridges without touching real pending.

    Real pending (non-empty payload or resume_path) is left unchanged.
    Does not clear verified/completed markers.
    """

    pending = request.session.get(PENDING_SESSION_KEY)
    if not isinstance(pending, dict):
        return
    payload = pending.get("payload") or {}
    resume = str(pending.get("resume_path") or "").strip()
    if payload or resume:
        return
    request.session.pop(PENDING_SESSION_KEY, None)
    request.session.modified = True


def bind_phone_challenge_to_new_challenge(
    request,
    *,
    challenge_id: str,
) -> dict[str, Any]:
    """After successful resend delivery, rebind phone_challenge to the new challenge."""

    phone = request.session.get(PHONE_CHALLENGE_SESSION_KEY)
    if not isinstance(phone, dict):
        raise RegistrationOTPSessionExpired(
            "Phone verification session expired. Please request a new code."
        )
    now = _utcnow()
    phone = dict(phone)
    phone["challenge_id"] = str(challenge_id)
    phone["resend_count"] = get_pending_resend_count(phone) + 1
    phone["last_resent_at"] = now.isoformat()
    request.session[PHONE_CHALLENGE_SESSION_KEY] = phone
    # Challenge replacement invalidates prior phone-verified proof for this session.
    request.session.pop(PHONE_VERIFIED_SESSION_KEY, None)
    request.session.modified = True
    return phone


def store_phone_verified(
    request,
    *,
    challenge_id: str,
    destination: str,
    flow_type: str,
    verified_at: str | None = None,
) -> dict[str, Any]:
    """Store temporary proof that a phone was OTP-verified for a registration flow.

    Does not store registration payload. Reuses pending-registration TTL for expiry.
    """

    now = _utcnow()
    verified_dt = _parse_iso(verified_at) if verified_at else now
    if verified_dt is None:
        verified_dt = now
    ttl = _pending_ttl_seconds()
    expires_at = verified_dt + timedelta(seconds=ttl)
    payload = {
        "challenge_id": str(challenge_id),
        "destination": str(destination).strip()[:32],
        "flow_type": str(flow_type),
        "verified_at": verified_dt.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    request.session[PHONE_VERIFIED_SESSION_KEY] = payload
    request.session.modified = True
    return payload


def is_phone_verified_expired(verified: Mapping[str, Any]) -> bool:
    """Return True when phone_verified expires_at (or verified_at+TTL) has elapsed."""

    expires = _parse_iso(verified.get("expires_at"))
    if expires is not None:
        return _utcnow() > expires
    verified_at = _parse_iso(verified.get("verified_at"))
    if verified_at is None:
        return True
    ttl = _pending_ttl_seconds()
    return _utcnow() > verified_at + timedelta(seconds=ttl)


def get_phone_verified(request, *, enforce_ttl: bool = True) -> dict[str, Any] | None:
    """Return phone_verified session or None (clears when expired if enforce_ttl)."""

    data = request.session.get(PHONE_VERIFIED_SESSION_KEY)
    if not isinstance(data, dict):
        return None
    if not data.get("challenge_id") or not data.get("flow_type"):
        return None
    if not data.get("destination"):
        return None
    if enforce_ttl and is_phone_verified_expired(data):
        clear_phone_verified(request)
        return None
    return data


def clear_phone_verified(request) -> None:
    """Clear phone_verified proof only."""

    request.session.pop(PHONE_VERIFIED_SESSION_KEY, None)
    request.session.modified = True


def consume_phone_verified_session(request) -> None:
    """Consume pre-registration phone proof after successful account creation.

    Clears phone_verified and companion phone_challenge. Safe no-op when absent.
    Call only after registration succeeds; keep proof on validation/DB failures.
    """

    clear_phone_verified(request)
    clear_phone_challenge(request)


def phone_verified_matches_registration(
    request,
    *,
    flow_type: str,
    destination: str | None,
) -> dict[str, Any] | None:
    """Return phone_verified when it may skip OTP for this registration submit.

    Validates destination, flow_type, and non-expiry via existing helpers.
    Does not trust client flags. Returns None when proof is missing/invalid.
    """

    from otp_verification.registration.adapters import normalize_destination
    from otp_verification.registration.exceptions import RegistrationOTPValidationError

    verified = get_phone_verified(request, enforce_ttl=True)
    if not verified:
        return None
    if str(verified.get("flow_type") or "") != str(flow_type):
        return None
    if not destination:
        return None
    try:
        submitted = normalize_destination(destination)
        stored = normalize_destination(str(verified.get("destination") or ""))
    except RegistrationOTPValidationError:
        return None
    if submitted != stored:
        return None
    if not str(verified.get("challenge_id") or "").strip():
        return None
    return verified


def _is_real_pending_registration(value: dict[str, Any] | None) -> bool:
    """True when pending holds a real paused registration (not an empty bridge)."""

    if not isinstance(value, dict):
        return False
    payload = value.get("payload") or {}
    resume = str(value.get("resume_path") or "").strip()
    return bool(payload) or bool(resume)


def resolve_otp_resend_session(
    request,
    *,
    enforce_ttl: bool = True,
) -> tuple[str, dict[str, Any] | None]:
    """Resolve which session resend should use.

    Preference:
    1. Real pending registration (non-empty payload or resume_path)
    2. Dedicated phone_challenge session
    3. Any remaining pending (legacy empty bridge compatibility)

    Returns ``(source, session)`` where source is ``\"pending\"`` or
    ``\"phone_challenge\"``. Session is None when neither is available.
    """

    raw_pending = request.session.get(PENDING_SESSION_KEY)
    phone = get_phone_challenge(request)

    if _is_real_pending_registration(raw_pending if isinstance(raw_pending, dict) else None):
        pending = get_pending_registration(request, enforce_ttl=enforce_ttl)
        return "pending", pending

    if phone:
        # Drop leftover empty bridges so they cannot collide with phone_challenge.
        discard_empty_pending_bridge(request)
        return "phone_challenge", phone

    pending = get_pending_registration(request, enforce_ttl=enforce_ttl)
    if pending:
        return "pending", pending
    return "", None


def store_pending_registration(
    request,
    *,
    flow_type: str,
    challenge_id: str,
    destination: str,
    payload: Mapping[str, Any],
    resume_path: str,
) -> None:
    """Persist minimal registration payload until OTP verification succeeds."""

    safe_payload = minimize_registration_payload(flow_type=flow_type, payload=payload)
    now = _utcnow()

    request.session[PENDING_SESSION_KEY] = {
        "flow_type": flow_type,
        "challenge_id": str(challenge_id),
        "destination": str(destination).strip()[:32],
        "payload": safe_payload,
        "resume_path": str(resume_path)[:500],
        "created_at": now.isoformat(),
        "resend_count": 0,
        "last_resent_at": now.isoformat(),
    }
    request.session[constants.SESSION_KEY_CHALLENGE_ID] = str(challenge_id)
    request.session[constants.SESSION_KEY_FLOW_TYPE] = flow_type
    # New OTP attempt invalidates prior verified/completed markers for this flow.
    request.session.pop(VERIFIED_SESSION_KEY, None)
    request.session.pop(COMPLETED_SESSION_KEY, None)
    request.session.pop(PHONE_VERIFIED_SESSION_KEY, None)
    request.session.modified = True


def _pending_ttl_seconds() -> int:
    try:
        return int(get_configuration().registration_pending_ttl_seconds)
    except Exception:  # noqa: BLE001 - safe default when config unavailable in tests
        return constants.DEFAULT_REGISTRATION_PENDING_TTL_SECONDS


def _completed_ttl_seconds() -> int:
    try:
        return int(get_configuration().registration_completed_ttl_seconds)
    except Exception:  # noqa: BLE001
        return constants.DEFAULT_REGISTRATION_COMPLETED_TTL_SECONDS


def is_pending_registration_expired(pending: Mapping[str, Any]) -> bool:
    """Return True when pending session age exceeds configured TTL."""

    created = _parse_iso(pending.get("created_at"))
    if created is None:
        # Legacy sessions without created_at: treat as expired so they cannot linger forever.
        return True
    ttl = _pending_ttl_seconds()
    return _utcnow() > created + timedelta(seconds=ttl)


def get_pending_registration(request, *, enforce_ttl: bool = True) -> dict[str, Any] | None:
    """Return pending registration or None.

    When ``enforce_ttl`` is True and the pending session is expired, the pending
    (and verified) markers are cleared and ``RegistrationOTPSessionExpired`` is raised.
    No partial users are created by this path.
    """

    pending = request.session.get(PENDING_SESSION_KEY)
    if not isinstance(pending, dict):
        return None
    if not pending.get("challenge_id") or not pending.get("flow_type"):
        return None
    if enforce_ttl and is_pending_registration_expired(pending):
        flow_type = pending.get("flow_type")
        challenge_id = pending.get("challenge_id")
        clear_pending_registration(request)
        logger.info(
            "event=%s flow=%s challenge=%s",
            AuditEvent.REGISTRATION_SESSION_EXPIRED,
            flow_type,
            challenge_id,
        )
        raise RegistrationOTPSessionExpired(
            "Registration session expired. Please register again."
        )
    return pending


def clear_pending_registration(request) -> None:
    """Clear pending + verified markers (does not clear completed idempotency marker)."""

    request.session.pop(PENDING_SESSION_KEY, None)
    request.session.pop(VERIFIED_SESSION_KEY, None)
    request.session.pop(PHONE_VERIFIED_SESSION_KEY, None)
    request.session.pop(PHONE_CHALLENGE_SESSION_KEY, None)
    request.session.pop(constants.SESSION_KEY_CHALLENGE_ID, None)
    request.session.pop(constants.SESSION_KEY_FLOW_TYPE, None)
    request.session.pop(constants.SESSION_KEY_VERIFIED_TOKEN, None)
    request.session.modified = True


def cancel_pending_registration(request) -> None:
    """Explicit cancel / abandon path — clears pending and verified state."""

    clear_pending_registration(request)


def mark_registration_otp_verified(
    request,
    *,
    challenge_id: str,
    flow_type: str,
) -> None:
    request.session[VERIFIED_SESSION_KEY] = {
        "challenge_id": str(challenge_id),
        "flow_type": flow_type,
        "verified_at": _utcnow().isoformat(),
    }
    request.session[constants.SESSION_KEY_VERIFIED_TOKEN] = str(challenge_id)
    request.session.modified = True


def is_registration_otp_verified(
    request,
    *,
    flow_type: str,
    challenge_id: str | None = None,
) -> bool:
    verified = request.session.get(VERIFIED_SESSION_KEY)
    if not isinstance(verified, dict):
        return False
    if verified.get("flow_type") != flow_type:
        return False
    if challenge_id and verified.get("challenge_id") != str(challenge_id):
        return False
    return True


def mark_registration_completed(
    request,
    *,
    challenge_id: str,
    flow_type: str,
    result: Mapping[str, Any] | None = None,
) -> None:
    """Record completion so double-submit returns idempotent success."""

    safe_result = {}
    if result:
        for key in ("flow_type", "user_id", "expert_id", "email"):
            if key in result:
                value = result[key]
                if key == "email" and value is not None:
                    safe_result[key] = str(value)[:_MAX_TEXT_LEN]
                else:
                    safe_result[key] = value
    request.session[COMPLETED_SESSION_KEY] = {
        "challenge_id": str(challenge_id),
        "flow_type": flow_type,
        "result": safe_result,
        "completed_at": _utcnow().isoformat(),
    }
    request.session.modified = True


def get_completed_registration(request) -> dict[str, Any] | None:
    completed = request.session.get(COMPLETED_SESSION_KEY)
    if not isinstance(completed, dict):
        return None
    completed_at = _parse_iso(completed.get("completed_at"))
    if completed_at is not None:
        ttl = _completed_ttl_seconds()
        if _utcnow() > completed_at + timedelta(seconds=ttl):
            clear_completed_registration(request)
            return None
    return completed


def clear_completed_registration(request) -> None:
    request.session.pop(COMPLETED_SESSION_KEY, None)
    request.session.modified = True


def finalize_registration_session(
    request,
    *,
    challenge_id: str,
    flow_type: str,
    result: Mapping[str, Any] | None = None,
) -> None:
    """Registration-layer finalization after successful user creation.

    Engine challenge status remains VERIFIED (ChallengeManager public API is
    unchanged). Replay protection already marked the challenge token consumed
    at verify time. This helper records the registration ``completed`` marker
    (session-level CONSUMED equivalent) and clears pending/verified state.
    Pending is never cleared before this is called on the success path.
    """

    mark_registration_completed(
        request,
        challenge_id=challenge_id,
        flow_type=flow_type,
        result=result,
    )
    clear_pending_registration(request)
    logger.info(
        "event=%s flow=%s challenge=%s",
        AuditEvent.REGISTRATION_FINALIZED,
        flow_type,
        challenge_id,
    )


def get_pending_resend_count(pending: Mapping[str, Any]) -> int:
    try:
        return max(0, int(pending.get("resend_count") or 0))
    except (TypeError, ValueError):
        return 0


def _generation_context_key(request, *, flow_type: str) -> str:
    # The Django session already owns/isolate this state. Keeping the key based
    # only on flow preserves the same budget across anonymous -> login changes.
    return str(flow_type)


def _legacy_successful_generation_count(request, *, flow_type: str) -> int:
    """Infer pre-feature successful generations from current challenge state."""

    inferred = 0
    for key in (PENDING_SESSION_KEY, PHONE_CHALLENGE_SESSION_KEY):
        state = request.session.get(key)
        if not isinstance(state, Mapping):
            continue
        if str(state.get("flow_type") or "") != str(flow_type):
            continue
        if not state.get("challenge_id"):
            continue
        inferred = max(inferred, 1 + get_pending_resend_count(state))
    return inferred


def get_otp_generation_count(request, *, flow_type: str) -> int:
    """Return successful OTP generations for this session-owned flow context."""

    budgets = request.session.get(GENERATION_BUDGET_SESSION_KEY)
    context_key = _generation_context_key(request, flow_type=flow_type)
    if isinstance(budgets, Mapping):
        state = budgets.get(context_key)
        if isinstance(state, Mapping):
            try:
                return max(0, int(state.get("generation_count") or 0))
            except (TypeError, ValueError):
                pass
    return _legacy_successful_generation_count(request, flow_type=flow_type)


def remaining_otp_generations(request, *, flow_type: str) -> int:
    used = get_otp_generation_count(request, flow_type=flow_type)
    return max(0, int(constants.MAX_OTP_GENERATIONS_PER_SESSION) - used)


def assert_otp_generation_available(request, *, flow_type: str) -> None:
    """Block before challenge/provider execution when five successes were used."""

    if remaining_otp_generations(request, flow_type=flow_type) <= 0:
        raise RegistrationOTPGenerationLimitReached(
            "Maximum OTP limit reached. Please try again later.",
            remaining_attempts=0,
        )


def record_successful_otp_generation(request, *, flow_type: str) -> int:
    """Record one provider-successful generation; referral state cannot reset it."""

    current = get_otp_generation_count(request, flow_type=flow_type)
    updated_count = current + 1
    raw_budgets = request.session.get(GENERATION_BUDGET_SESSION_KEY)
    budgets = dict(raw_budgets) if isinstance(raw_budgets, Mapping) else {}
    context_key = _generation_context_key(request, flow_type=flow_type)
    previous = budgets.get(context_key)
    previous_state = dict(previous) if isinstance(previous, Mapping) else {}
    now = _utcnow().isoformat()
    user = getattr(request, "user", None)
    user_id = (
        getattr(user, "pk", None)
        if user is not None and getattr(user, "is_authenticated", False)
        else None
    )
    budgets[context_key] = {
        "flow_type": str(flow_type),
        "user_id": str(user_id) if user_id is not None else None,
        "generation_count": updated_count,
        "started_at": previous_state.get("started_at") or now,
        "last_success_at": now,
    }
    request.session[GENERATION_BUDGET_SESSION_KEY] = budgets
    request.session.modified = True
    return updated_count


def cooldown_remaining_seconds(pending: Mapping[str, Any], *, cooldown_seconds: int) -> int:
    """Seconds until resend is allowed (0 if ready)."""

    if cooldown_seconds <= 0:
        return 0
    anchor = _parse_iso(pending.get("last_resent_at")) or _parse_iso(pending.get("created_at"))
    if anchor is None:
        return 0
    elapsed = (_utcnow() - anchor).total_seconds()
    remaining = int(cooldown_seconds - elapsed)
    return max(0, remaining)


def bind_pending_to_new_challenge(
    request,
    *,
    challenge_id: str,
) -> dict[str, Any]:
    """After successful resend delivery, rebind pending to the new challenge."""

    pending = request.session.get(PENDING_SESSION_KEY)
    if not isinstance(pending, dict):
        raise RegistrationOTPSessionExpired(
            "Registration session expired. Please register again."
        )
    now = _utcnow()
    pending = dict(pending)
    pending["challenge_id"] = str(challenge_id)
    pending["resend_count"] = get_pending_resend_count(pending) + 1
    pending["last_resent_at"] = now.isoformat()
    # created_at intentionally unchanged — pending TTL does not reset.
    request.session[PENDING_SESSION_KEY] = pending
    request.session[constants.SESSION_KEY_CHALLENGE_ID] = str(challenge_id)
    request.session.pop(VERIFIED_SESSION_KEY, None)
    request.session.pop(PHONE_VERIFIED_SESSION_KEY, None)
    request.session.modified = True
    return pending
