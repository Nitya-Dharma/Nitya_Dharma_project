"""
Service functions for email verification resend authority.

TASK 11: Email verification resend authority.

Pandit self-service does not change the recorded sender. The first Admin
Pandit or Super Admin resend may record a sender only when none exists.
Later resends preserve that sender. Super Admin recovery does not replace it.
Deactivation does not rewrite sender rows.
"""

import logging

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import EmailVerificationToken

User = get_user_model()
logger = logging.getLogger(__name__)


def authoritative_verification_token(user):
    """Return the token that currently records resend authority.

    The latest token with a sender wins. If no token has a sender, the latest
    token is returned so a null sender stays visible. Missing history returns
    None.
    """
    if user is None or getattr(user, "pk", None) is None:
        return None

    recorded_sender = (
        EmailVerificationToken.objects.filter(user=user, sent_by__isnull=False)
        .select_related("sent_by", "user")
        .order_by("-created_at", "-pk")
        .first()
    )
    if recorded_sender is not None:
        return recorded_sender

    return (
        EmailVerificationToken.objects.filter(user=user)
        .select_related("sent_by", "user")
        .order_by("-created_at", "-pk")
        .first()
    )


def can_resend_verification(token, actor, target_user=None):
    """Return whether this HTTP actor may resend for the target Pandit.

    Shell calls do not use this function. A null token means no sender has
    been recorded. Pandit self-service is allowed for an inactive pending
    Pandit. Admin and Super Admin actors must be active.
    """
    if actor is None:
        return False

    target = target_user if target_user is not None else getattr(token, "user", None)
    if target is None:
        return False
    if token is not None and token.user_id != target.pk:
        return False

    if getattr(actor, "role", None) == "pandit":
        return actor.pk == target.pk

    if not getattr(actor, "is_active", False):
        return False

    if getattr(actor, "is_superuser", False):
        return True

    if getattr(actor, "role", None) != "admin":
        return False

    sender = token.sent_by if token is not None else None
    if sender is None:
        return True
    return bool(sender.is_active and sender.pk == actor.pk)


def resend_verification_email(token, actor):
    """Resend through the shared Pandit resend service.

    Delivery, token replacement, cooldown, and the daily limit stay in
    accounts.services.resend_verification_email. This function does not send
    mail and does not assign sent_by.
    """
    if token is None:
        raise ValidationError("A verification token is required.")
    if actor is None:
        raise ValidationError("An authorized user is required.")
    if not can_resend_verification(token, actor, target_user=token.user):
        raise ValidationError("You are not authorized to resend this verification email.")

    from accounts.services import resend_verification_email as resend_for_user

    return resend_for_user(token.user, requested_by=actor)


def handle_admin_pandit_verification_authority_transfer(admin_pandit, actor=None):
    """
    TASK 11: Transfer email verification resend authority when Admin Pandit is deactivated.
    
    This function:
    - Ensures pending Pandits remain pending
    - Verification resend remains possible
    - Super Admin becomes resend authority automatically
    
    Args:
        admin_pandit: User instance (must have role='admin')
        actor: User instance (Super Admin performing deactivation)
    
    Returns:
        dict: Summary of authority transfer
    
    Raises:
        ValidationError: If user is not an Admin Pandit
    """
    if admin_pandit.role != 'admin':
        raise ValidationError(f"User {admin_pandit.email} is not an Admin Pandit.")
    
    with transaction.atomic():
        # Find all verification tokens sent by this Admin Pandit
        tokens = EmailVerificationToken.objects.filter(sent_by=admin_pandit)
        token_count = tokens.count()
        
        if token_count == 0:
            logger.info("Admin Pandit sent no verification emails - user_id=%s", admin_pandit.pk)
            return {
                'token_count': 0,
                'tokens_affected': [],
                'message': 'No verification tokens to transfer'
            }
        
        # sent_by is preserved (SET_NULL on delete, but we're deactivating, not deleting)
        # When Admin Pandit is deactivated, sent_by remains but is inactive
        # Super Admin can now resend (checked in can_resend_verification)
        
        
        logger.info(
            "Email verification resend authority transferred - "
            "admin_user_id=%s, tokens_affected=%s",
            admin_pandit.pk,
            token_count,
        )
        
        return {
            'token_count': token_count,
            'tokens_affected': [t.id for t in tokens],
            'message': f'{token_count} verification token(s) - Super Admin can now resend'
        }
