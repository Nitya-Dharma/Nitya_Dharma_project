"""Shared referral validation for Pandit registration."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

try:
    from referrals.models import ReferralLink
except ImportError:  # pragma: no cover - referrals app optional in some contexts
    ReferralLink = None  # type: ignore[misc, assignment]

REFERRAL_SYSTEM_UNAVAILABLE = (
    "Referral system is not available. Please contact support."
)


@dataclass(frozen=True)
class ReferralValidationResult:
    referral_link: ReferralLink | None
    is_valid: bool
    error_message: str | None = None


def referral_system_available() -> bool:
    return ReferralLink is not None


def lookup_referral_link_by_url_token(referral_token: str):
    """Resolve a referral link from the URL segment (token, referral_code, or code)."""

    if ReferralLink is None:
        return None
    token = (referral_token or "").strip()
    if not token:
        return None
    referral_link = ReferralLink.objects.filter(token=token).first()
    if referral_link is None:
        referral_link = ReferralLink.objects.filter(referral_code=token).first()
    if referral_link is None:
        referral_link = ReferralLink.objects.filter(code=token).first()
    return referral_link


def get_referral_not_found_message() -> str:
    if ReferralLink is None:
        return REFERRAL_SYSTEM_UNAVAILABLE
    if ReferralLink.objects.count() == 0:
        return (
            "No referral links have been generated yet. Please ask an Admin Pandit to "
            "generate a referral link from their dashboard."
        )
    return (
        "Referral token does not exist or is invalid. Please check your referral link "
        "and ensure it was copied correctly."
    )


def referral_code_matches(link, submitted_code: str) -> bool:
    """Return True when submitted code matches legacy or current referral identifiers."""

    code = (submitted_code or "").strip()
    if not code:
        return False
    candidates: list[str] = []
    for value in (getattr(link, "referral_code", None), getattr(link, "code", None)):
        if value:
            text = str(value).strip()
            if text and text not in candidates:
                candidates.append(text)
    return code in candidates


def validate_referral_link_state(referral_link) -> ReferralValidationResult:
    """Validate referral link lifecycle rules and referrer active status."""

    if referral_link is None:
        return ReferralValidationResult(None, False, get_referral_not_found_message())

    if not referral_link.is_active:
        return ReferralValidationResult(
            referral_link,
            False,
            "This referral link has been deactivated and cannot be used for registration.",
        )

    if referral_link.used_count >= referral_link.max_uses:
        return ReferralValidationResult(
            referral_link,
            False,
            f"This referral link has reached its maximum usage limit ({referral_link.max_uses} uses).",
        )

    if referral_link.status != ReferralLink.STATUS_ACTIVE:
        return ReferralValidationResult(
            referral_link,
            False,
            f"This referral link is {referral_link.get_status_display().lower()} and cannot be used.",
        )

    if getattr(referral_link, "expires_at", None) and referral_link.expires_at < timezone.now():
        return ReferralValidationResult(
            referral_link,
            False,
            "This referral link has expired.",
        )

    referrer = referral_link.created_by
    if referrer is not None and (referrer.status != "active" or not referrer.is_active):
        return ReferralValidationResult(
            referral_link,
            False,
            "The referrer account is not active. This referral link cannot be used.",
        )

    return ReferralValidationResult(referral_link, True, None)


def validate_referral_for_pandit_get(referral_token: str) -> ReferralValidationResult:
    """GET entry validation: lookup by URL token and validate link state."""

    if ReferralLink is None:
        return ReferralValidationResult(None, False, REFERRAL_SYSTEM_UNAVAILABLE)

    referral_link = lookup_referral_link_by_url_token(referral_token)
    if referral_link is None:
        return ReferralValidationResult(None, False, get_referral_not_found_message())
    return validate_referral_link_state(referral_link)


def validate_referral_for_pandit_post(
    referral_token: str,
    referral_code: str,
) -> ReferralValidationResult:
    """POST validation: lookup, code match, then link state."""

    if ReferralLink is None:
        return ReferralValidationResult(None, False, REFERRAL_SYSTEM_UNAVAILABLE)

    referral_link = lookup_referral_link_by_url_token(referral_token)
    if referral_link is None:
        return ReferralValidationResult(None, False, "Referral token does not exist or is invalid")

    if not referral_code_matches(referral_link, referral_code):
        return ReferralValidationResult(
            referral_link,
            False,
            "Referral code does not match the referral token",
        )

    state = validate_referral_link_state(referral_link)
    if not state.is_valid:
        message = state.error_message or "Invalid referral link."
        if "deactivated" in message:
            message = "This referral link has been deactivated and cannot be used for registration"
        elif "maximum usage limit" in message:
            pass  # keep GET-style message for POST JSON compatibility
        return ReferralValidationResult(referral_link, False, message)

    return ReferralValidationResult(referral_link, True, None)


def validate_referral_link_by_id(
    referral_link_id: int | None,
    referral_code: str | None = None,
) -> ReferralValidationResult:
    """Final OTP-completion validation using stored referral_link_id."""

    if ReferralLink is None:
        return ReferralValidationResult(None, False, REFERRAL_SYSTEM_UNAVAILABLE)

    if referral_link_id is None:
        return ReferralValidationResult(
            None,
            False,
            "Referral link is required for Pandit registration.",
        )

    try:
        link_id = int(referral_link_id)
    except (TypeError, ValueError):
        return ReferralValidationResult(
            None,
            False,
            "Referral link is required for Pandit registration.",
        )

    referral_link = ReferralLink.objects.filter(id=link_id).first()
    if referral_link is None:
        return ReferralValidationResult(
            None,
            False,
            "Referral token does not exist or is invalid",
        )

    if referral_code and not referral_code_matches(referral_link, referral_code):
        return ReferralValidationResult(
            referral_link,
            False,
            "Referral code does not match the referral token",
        )

    return validate_referral_link_state(referral_link)
