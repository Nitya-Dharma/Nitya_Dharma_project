"""Bureau owner email verification resend (self-service only)."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction
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

    The caller is the Bureau owner. Cooldown and the five-token limit run
    inside the transaction after the owner row is locked. The limit counts
    tokens created in the last 24 hours when the last-sent timestamp is
    null or older than that window. Token creation and mail scheduling stay
    in create_email_verification.
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

    try:
        with transaction.atomic():
            if connection.features.has_select_for_update:
                locked_user = User.objects.select_for_update().get(pk=user.pk)
            else:
                locked_user = User.objects.get(pk=user.pk)

            if locked_user.email_verified or locked_user.email_verified_at:
                raise BureauVerificationAlreadyCompleted(
                    "User email is already verified"
                )

            now = timezone.now()
            last_sent_at = locked_user.last_verification_email_sent_at
            if last_sent_at is not None and now - last_sent_at < timedelta(seconds=30):
                remaining_seconds = 30 - int((now - last_sent_at).total_seconds())
                raise BureauResendCooldownNotElapsed(
                    f"Please wait {remaining_seconds} seconds before requesting "
                    "another verification email"
                )

            recent_tokens = EmailVerificationToken.objects.filter(
                user=locked_user,
                created_at__gte=now - timedelta(days=1),
            ).count()
            if recent_tokens >= 5:
                raise ValidationError(
                    "Maximum verification email attempts reached. "
                    "Please try again tomorrow."
                )

            locked_user.last_verification_email_sent_at = now
            locked_user.save(update_fields=["last_verification_email_sent_at"])

            logger.info(
                "[BUREAU EMAIL RESEND] Resending verification email for %s",
                locked_user.email,
            )
            verification_token = create_email_verification(locked_user)
            logger.info(
                "[BUREAU EMAIL RESEND] Verification email resent for %s",
                locked_user.email,
            )
            return verification_token
    except ValidationError:
        raise
    except Exception as exc:
        logger.error(
            "Error resending Bureau verification email",
            extra={"error_type": type(exc).__name__},
        )
        raise
