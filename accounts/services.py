"""
Account Services (TASK 2: Email Verification Resend Service)

This module contains service functions for account management operations.
All business logic is centralized here, separate from views.
"""

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from .email_verification import create_email_verification
from .models import EmailVerificationToken, User

logger = logging.getLogger(__name__)

RESEND_COOLDOWN = timedelta(seconds=30)
RESEND_DAILY_WINDOW = timedelta(days=1)
RESEND_DAILY_LIMIT = 5
RESEND_UNAUTHORIZED = "You are not authorized to resend this verification email."


class VerificationAlreadyCompleted(ValidationError):
    """Raised when trying to resend verification for already verified user."""
    pass


class CooldownNotElapsed(ValidationError):
    """Raised when resend is attempted before cooldown period."""
    pass


def _sent_by_for_replacement(existing_sent_by, requested_by):
    """Choose the sender stored on the replacement token.

    An existing sender is always preserved. A shell call or Pandit
    self-resend must not invent one. The first Admin Pandit or Super
    Admin resend may establish a sender only while it is null.
    """
    if existing_sent_by is not None:
        return existing_sent_by
    if requested_by is None or getattr(requested_by, "role", None) == "pandit":
        return None
    if getattr(requested_by, "is_superuser", False) or getattr(requested_by, "role", None) == "admin":
        return requested_by
    return None


def _cooldown_remaining(user, now):
    last_sent_at = user.last_verification_email_sent_at
    if last_sent_at is None:
        return None
    elapsed = now - last_sent_at
    if elapsed >= RESEND_COOLDOWN:
        return None
    return RESEND_COOLDOWN.seconds - int(elapsed.total_seconds())


def resend_verification_email(user, requested_by=None):
    """
    Resends verification email if:
    - user is Pandit
    - user.email_verified is False (or email_verified_at is None)
    - last email was sent more than 30 seconds ago
    - fewer than five verification tokens were created in the last 24 hours

    HTTP callers pass requested_by and are authorized against the current
    sender. A shell call leaves requested_by empty and does not invent an actor.

    Args:
        user: User instance (Pandit) to resend verification for
        requested_by: User instance who requested the resend, or None for the
            management command and other operator shell calls

    Returns:
        EmailVerificationToken: Created verification token

    Raises:
        VerificationAlreadyCompleted: If user is already verified
        CooldownNotElapsed: If resend attempted within 30 seconds
        ValidationError: If user is not a Pandit, the actor is not authorized,
            or the daily token limit has been reached
    """
    if not user or not isinstance(user, User):
        raise ValidationError("Valid user instance required")

    if user.role != "pandit":
        raise ValidationError("Email verification resend is only available for Pandit accounts")

    if user.email_verified or user.email_verified_at:
        raise VerificationAlreadyCompleted("User email is already verified")

    from .services_email_verification_authority import (
        authoritative_verification_token,
        can_resend_verification,
    )

    if requested_by is not None:
        current_token = authoritative_verification_token(user)
        if not can_resend_verification(current_token, requested_by, target_user=user):
            raise ValidationError(RESEND_UNAUTHORIZED)

    try:
        with transaction.atomic():
            if connection.features.has_select_for_update:
                locked_user = User.objects.select_for_update().get(pk=user.pk)
            else:
                locked_user = User.objects.get(pk=user.pk)

            if locked_user.role != "pandit":
                raise ValidationError(
                    "Email verification resend is only available for Pandit accounts"
                )
            if locked_user.email_verified or locked_user.email_verified_at:
                raise VerificationAlreadyCompleted("User email is already verified")

            actor = requested_by
            if actor is not None:
                actor = User.objects.get(pk=actor.pk)

            now = timezone.now()
            current_token = authoritative_verification_token(locked_user)
            if current_token is not None and current_token.sent_by_id:
                current_token.sent_by.refresh_from_db(fields=["is_active", "role"])

            if actor is not None and not can_resend_verification(
                current_token,
                actor,
                target_user=locked_user,
            ):
                raise ValidationError(RESEND_UNAUTHORIZED)

            remaining_seconds = _cooldown_remaining(locked_user, now)
            if remaining_seconds is not None:
                raise CooldownNotElapsed(
                    "Please wait "
                    f"{remaining_seconds} seconds before requesting another verification email"
                )

            recent_tokens = EmailVerificationToken.objects.filter(
                user=locked_user,
                created_at__gte=now - RESEND_DAILY_WINDOW,
            ).count()
            if recent_tokens >= RESEND_DAILY_LIMIT:
                raise ValidationError(
                    "Maximum verification email attempts reached. Please try again tomorrow."
                )

            existing_sent_by = current_token.sent_by if current_token is not None else None
            sent_by = _sent_by_for_replacement(existing_sent_by, actor)

            locked_user.last_verification_email_sent_at = now
            locked_user.save(update_fields=["last_verification_email_sent_at"])

            logger.info("[EMAIL RESEND] Resending verification email for %s", locked_user.email)
            logger.info(
                "[EMAIL RESEND] Requested by: %s",
                actor.email if actor is not None else "self",
            )

            # Token replacement and delivery stay in create_email_verification,
            # including invalidation of the previous active token and on_commit.
            verification_token = create_email_verification(locked_user, sent_by=sent_by)

            logger.info(
                "[EMAIL RESEND] Verification email resent successfully for %s",
                locked_user.email,
            )

            try:
                from analytics.audit_events import log_audit_event
                from referrals.constants import AUDIT_ACTION_EMAIL_VERIFICATION_SENT

                log_audit_event(
                    event_type=AUDIT_ACTION_EMAIL_VERIFICATION_SENT,
                    user=actor or locked_user,
                    metadata={
                        "action": "resend_verification",
                        "target_user_id": locked_user.id,
                        "target_user_email": locked_user.email,
                        "token_id": verification_token.public_id,
                        "result": "sent",
                        "requested_by": actor.email if actor is not None else locked_user.email,
                        "requested_by_id": actor.pk if actor is not None else None,
                        "preserved_sent_by_id": sent_by.pk if sent_by is not None else None,
                    },
                )
            except Exception as audit_error:
                logger.warning(
                    "Failed to log audit event for resend verification: %s",
                    audit_error,
                )

            logger.info(
                "Verification email resent for user %s (requested by: %s)",
                locked_user.email,
                actor.email if actor is not None else "self",
            )
            return verification_token
    except ValidationError:
        raise
    except Exception as exc:
        logger.error(
            "Error resending verification email for user %s: %s",
            getattr(user, "email", None),
            exc,
            exc_info=True,
        )
        raise
