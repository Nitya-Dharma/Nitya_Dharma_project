"""Bureau owner email verification resend (self-service only)."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.email_verification import create_email_verification
from accounts.models import EmailVerificationToken

from .models import BureauProfile

logger = logging.getLogger(__name__)

User = get_user_model()


class BureauVerificationAlreadyCompleted(ValidationError):
    """Raised when Bureau owner email is already verified."""


class BureauResendCooldownNotElapsed(ValidationError):
    """Raised when resend is attempted before cooldown period."""


class BureauResendNotAllowed(ValidationError):
    """Raised when the user is not a Bureau owner."""


def _get_owned_bureau_profile(user) -> BureauProfile | None:
    try:
        return BureauProfile.objects.get(user=user)
    except BureauProfile.DoesNotExist:
        return None


def resend_bureau_verification_email(user):
    """Resend Bureau owner email verification using shared token infrastructure.

    Mirrors Pandit resend cooldown/daily-limit semantics without calling
    accounts.services.resend_verification_email().
    """
    if not user or not isinstance(user, User):
        raise ValidationError("Valid user instance required")

    bureau_profile = _get_owned_bureau_profile(user)
    if bureau_profile is None:
        raise BureauResendNotAllowed(
            "Email verification resend is only available for Bureau owner accounts."
        )

    if user.email_verified or user.email_verified_at:
        raise BureauVerificationAlreadyCompleted("User email is already verified")

    if user.last_verification_email_sent_at:
        time_since_last = timezone.now() - user.last_verification_email_sent_at
        if time_since_last < timedelta(seconds=30):
            remaining_seconds = 30 - int(time_since_last.total_seconds())
            raise BureauResendCooldownNotElapsed(
                f"Please wait {remaining_seconds} seconds before requesting "
                "another verification email"
            )

    one_day_ago = timezone.now() - timedelta(days=1)
    if (
        user.last_verification_email_sent_at
        and user.last_verification_email_sent_at >= one_day_ago
    ):
        recent_tokens = EmailVerificationToken.objects.filter(
            user=user,
            created_at__gte=one_day_ago,
        ).count()
        if recent_tokens >= 5:
            raise ValidationError(
                "Maximum verification email attempts reached. "
                "Please try again tomorrow."
            )

    try:
        with transaction.atomic():
            user.last_verification_email_sent_at = timezone.now()
            user.save(update_fields=["last_verification_email_sent_at"])

            logger.info(
                "[BUREAU EMAIL RESEND] Resending verification email for %s",
                user.email,
            )
            verification_token = create_email_verification(user)
            logger.info(
                "[BUREAU EMAIL RESEND] Verification email resent for %s",
                user.email,
            )
            return verification_token
    except Exception:
        logger.exception(
            "Error resending Bureau verification email for %s",
            user.email,
        )
        raise
