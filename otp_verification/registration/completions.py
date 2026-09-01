"""Complete paused registrations after successful OTP verification."""

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from otp_verification import constants

logger = logging.getLogger(__name__)
User = get_user_model()


class CompletionError(Exception):
    """Raised when pending registration cannot be completed."""


class AlreadyCompletedError(CompletionError):
    """Registration for this identity already exists (idempotent conflict)."""

    def __init__(self, message: str, *, result: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.result = result or {}


def complete_pending_registration(*, pending: dict[str, Any]) -> dict[str, Any]:
    """Dispatch completion by flow_type using stored session payload."""

    flow_type = pending.get("flow_type")
    payload = pending.get("payload") or {}
    if flow_type == constants.FLOW_USER_REGISTRATION:
        return _complete_user(payload)
    if flow_type == constants.FLOW_BUREAU_REGISTRATION:
        return _complete_bureau(payload)
    if flow_type == constants.FLOW_EXPERT_REGISTRATION:
        return _complete_expert(payload)
    if flow_type == constants.FLOW_PANDIT_REGISTRATION:
        return _complete_pandit(payload)
    raise CompletionError(f"Unsupported registration flow '{flow_type}'.")


def _password_from_payload(payload: dict[str, Any]) -> str | None:
    return payload.get("password_hash")


def _apply_password_hash(user, password_hash: str | None) -> None:
    if password_hash:
        user.password = password_hash
        user.save(update_fields=["password"])


def _sync_expert_user_phone(user, phone: str) -> None:
    phone = (phone or "").strip()
    if not user or not phone or not hasattr(user, "phone_number"):
        return
    if user.phone_number != phone:
        user.phone_number = phone
        user.save(update_fields=["phone_number", "updated_at"])


def mark_expert_user_phone_verified(*, email: str, phone: str) -> None:
    """Persist phone verification on the Expert owner's User row (no activation)."""

    email = (email or "").strip()
    phone = (phone or "").strip()
    if not email or not phone:
        return
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return
    _sync_expert_user_phone(user, phone)
    if getattr(user, "is_phone_verified", False):
        return
    from django.utils import timezone

    user.is_phone_verified = True
    user.phone_verified_at = timezone.now()
    user.save(
        update_fields=[
            "phone_number",
            "is_phone_verified",
            "phone_verified_at",
            "updated_at",
        ]
    )


def mark_bureau_user_phone_verified(*, email: str, phone: str) -> None:
    """Persist phone verification on the Bureau owner's User row (no activation)."""

    email = (email or "").strip()
    phone = (phone or "").strip()
    if not email or not phone:
        return
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return
    _sync_expert_user_phone(user, phone)
    if getattr(user, "is_phone_verified", False):
        return
    from django.utils import timezone

    user.is_phone_verified = True
    user.phone_verified_at = timezone.now()
    user.save(
        update_fields=[
            "phone_number",
            "is_phone_verified",
            "phone_verified_at",
            "updated_at",
        ]
    )


def _complete_user(payload: dict[str, Any]) -> dict[str, Any]:
    email = (payload.get("email") or "").strip()
    if not email:
        raise CompletionError("Missing email for user registration.")

    with transaction.atomic():
        existing = User.objects.filter(email__iexact=email).first()
        if existing is not None:
            raise AlreadyCompletedError(
                "A user with this email address already exists.",
                result={
                    "flow_type": constants.FLOW_USER_REGISTRATION,
                    "user_id": existing.id,
                    "email": existing.email,
                },
            )

        password_hash = _password_from_payload(payload)
        user = User.objects.create_user(
            email=email,
            password="!",
            first_name=(payload.get("first_name") or "").strip(),
            last_name=(payload.get("last_name") or "").strip(),
            role="user",
            status="active",
            is_active=True,
            email_verified=False,
        )
        _apply_password_hash(user, password_hash)
        phone = (payload.get("phone") or payload.get("phone_number") or "").strip()
        if phone and hasattr(user, "phone_number"):
            user.phone_number = phone
            user.save(update_fields=["phone_number"])

        try:
            from accounts.email_verification import create_email_verification

            create_email_verification(user)
        except Exception:
            logger.exception("Failed to create email verification after OTP")

    return {"flow_type": constants.FLOW_USER_REGISTRATION, "user_id": user.id, "email": user.email}


def _complete_bureau(payload: dict[str, Any]) -> dict[str, Any]:
    from bureaus.models import BureauProfile
    from bureaus.views import _build_random_bureau_username, _email_exists_ci

    email = (payload.get("email") or "").strip()
    if not email:
        raise CompletionError("Missing email for bureau registration.")
    password_hash = _password_from_payload(payload)
    if not password_hash:
        raise CompletionError("Missing password for bureau registration.")

    with transaction.atomic():
        if _email_exists_ci(User, email):
            existing = User.objects.filter(email__iexact=email).first()
            raise AlreadyCompletedError(
                "An account with this email already exists.",
                result={
                    "flow_type": constants.FLOW_BUREAU_REGISTRATION,
                    "user_id": getattr(existing, "id", None),
                    "email": email,
                },
            )
        user = None
        for _ in range(5):
            try:
                user = User.objects.create_user(
                    email=email,
                    password="!",
                    username=_build_random_bureau_username(),
                    role="user",
                    status="active",
                    is_active=True,
                )
                break
            except IntegrityError:
                if _email_exists_ci(User, email):
                    raise AlreadyCompletedError(
                        "An account with this email already exists.",
                        result={"flow_type": constants.FLOW_BUREAU_REGISTRATION, "email": email},
                    )
                continue
        if user is None:
            raise CompletionError("Registration failed. Please try again.")
        _apply_password_hash(user, password_hash)
        if BureauProfile.objects.select_for_update().filter(user=user).exists():
            raise AlreadyCompletedError(
                "A bureau profile already exists for this account.",
                result={
                    "flow_type": constants.FLOW_BUREAU_REGISTRATION,
                    "user_id": user.id,
                    "email": email,
                },
            )
        phone_number = (payload.get("phone_number") or "").strip()
        BureauProfile.objects.create(
            user=user,
            bureau_name=payload.get("bureau_name") or "",
            phone_number=phone_number,
            address=payload.get("address") or "",
            city=payload.get("city") or "",
            whatsapp_number=payload.get("whatsapp_number") or "",
            is_active=False,
            is_approved=False,
            is_email_verified=False,
        )
        _sync_expert_user_phone(user, phone_number)
        try:
            from accounts.email_verification import create_email_verification

            create_email_verification(user)
        except Exception:
            logger.exception("Failed to create email verification after bureau OTP")

    return {"flow_type": constants.FLOW_BUREAU_REGISTRATION, "user_id": user.id, "email": email}


def _complete_expert(payload: dict[str, Any]) -> dict[str, Any]:
    from core.models import ExpertProfile
    from services.expert_service_selection import (
        ExpertServiceSelectionError,
        primary_expert_type,
        resolve_active_services_by_slugs,
    )
    from services.models import ExpertSocialLink

    email = (payload.get("email") or "").strip()
    phone = (payload.get("phone") or "").strip()
    name = (payload.get("name") or "").strip()
    password_hash = _password_from_payload(payload)
    social_links = payload.get("social_links") or []
    if not isinstance(social_links, list):
        social_links = []
    raw_service_slugs = payload.get("service_slugs") or []
    if not isinstance(raw_service_slugs, list):
        raise CompletionError("Invalid services for expert registration.")

    with transaction.atomic():
        try:
            selected_services = resolve_active_services_by_slugs(
                raw_service_slugs
            )
        except ExpertServiceSelectionError as exc:
            raise CompletionError(str(exc)) from exc

        existing = ExpertProfile.objects.filter(phone=phone).first()
        if not existing and email:
            existing = ExpertProfile.objects.filter(email=email).first()
        if existing is not None:
            raise AlreadyCompletedError(
                "An account with this phone or email already exists.",
                result={
                    "flow_type": constants.FLOW_EXPERT_REGISTRATION,
                    "expert_id": existing.id,
                    "email": email,
                },
            )

        if email:
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password="!",
                )
                _apply_password_hash(user, password_hash)
            _sync_expert_user_phone(user, phone)

        expert = ExpertProfile.objects.create(
            name=name,
            email=email,
            phone=phone,
            experience_years=int(payload.get("experience_years") or 0),
            description=payload.get("description") or "",
            expert_type=primary_expert_type(selected_services),
            is_active=False,
            is_verified=False,
        )
        expert.services.set(selected_services)
        for link in social_links:
            if link:
                ExpertSocialLink.objects.create(expert=expert, url=link)

    return {
        "flow_type": constants.FLOW_EXPERT_REGISTRATION,
        "expert_id": expert.id,
        "email": email,
    }


def _complete_pandit(payload: dict[str, Any]) -> dict[str, Any]:
    from accounts.email_verification import create_email_verification

    email = (payload.get("email") or "").strip()
    if not email:
        raise CompletionError("Missing email for pandit registration.")

    password_hash = _password_from_payload(payload)
    referral_link_id = payload.get("referral_link_id")
    referral_code = payload.get("referral_code")

    from referrals.registration_validation import validate_referral_link_by_id

    referral_validation = validate_referral_link_by_id(referral_link_id, referral_code)
    if not referral_validation.is_valid or referral_validation.referral_link is None:
        raise CompletionError(
            referral_validation.error_message or "Invalid referral link for Pandit registration."
        )
    referral_link = referral_validation.referral_link

    with transaction.atomic():
        existing = User.objects.filter(email__iexact=email).first()
        if existing is not None:
            raise AlreadyCompletedError(
                "A user with this email address already exists.",
                result={
                    "flow_type": constants.FLOW_PANDIT_REGISTRATION,
                    "user_id": existing.id,
                    "email": existing.email,
                },
            )

        user = User.objects.create_user(
            email=email,
            password="!",
            first_name=(payload.get("first_name") or "").strip(),
            last_name=(payload.get("last_name") or "").strip(),
            role="pandit",
            status="pending",
            is_active=False,
            email_verified=False,
        )
        _apply_password_hash(user, password_hash)
        phone = (payload.get("phone") or payload.get("phone_number") or "").strip()
        if phone and hasattr(user, "phone_number"):
            user.phone_number = phone
            user.save(update_fields=["phone_number"])

        from profiles.models import PanditProfile

        # Must succeed inside the atomic block — do not swallow failures
        # (would otherwise commit a pandit User without PanditProfile).
        PanditProfile.objects.get_or_create(user=user)

        from referrals.models import ReferralLink, ReferralUsage

        locked_referral_link = (
            ReferralLink.objects.select_for_update().filter(id=referral_link.id).first()
        )
        if locked_referral_link is None:
            raise CompletionError("Referral token does not exist or is invalid")

        revalidation = validate_referral_link_by_id(locked_referral_link.id, referral_code)
        if not revalidation.is_valid or revalidation.referral_link is None:
            raise CompletionError(
                revalidation.error_message or "Invalid referral link for Pandit registration."
            )

        already_used = ReferralUsage.objects.filter(
            referral_link=locked_referral_link,
            referred_pandit=user,
        ).exists()
        if not already_used:
            user.referred_by = locked_referral_link.created_by
            user.save(update_fields=["referred_by"])
            locked_referral_link.used_count += 1
            if locked_referral_link.used_count >= locked_referral_link.max_uses:
                locked_referral_link.is_active = False
            locked_referral_link.save()
            ReferralUsage.objects.create(
                referral_link=locked_referral_link,
                referred_pandit=user,
            )

        try:
            create_email_verification(user)
        except Exception:
            logger.exception("Email verification failed after pandit OTP")

    return {
        "flow_type": constants.FLOW_PANDIT_REGISTRATION,
        "user_id": user.id,
        "email": user.email,
    }
