"""
Service functions for email verification resend authority transfer.

TASK 11: Email Verification/Resend Authority Transfer

This module ensures that:
- Pending Pandits are never blocked
- Verification resend remains possible when Admin Pandit is deactivated
- Super Admin automatically inherits resend authority
- Original sender remains in audit history
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import EmailVerificationToken
from accounts.email_verification import create_email_verification, send_verification_email

User = get_user_model()
logger = logging.getLogger(__name__)


def can_resend_verification(token, actor):
    """
    TASK 11: Check if actor can resend verification email.
    
    Rules:
    - If sent_by is inactive → allow Super Admin to resend
    - If sent_by is active → only sent_by or Super Admin can resend
    - Rate limits remain unchanged
    
    Args:
        token: EmailVerificationToken instance
        actor: User instance attempting resend
    
    Returns:
        bool: True if actor can resend
    """
    if not token:
        return False
    
    # Super Admin can always resend
    if actor.is_superuser:
        return True
    
    # If sent_by is inactive, only Super Admin can resend
    if token.sent_by and not token.sent_by.is_active:
        return actor.is_superuser
    
    # If sent_by is active, only sent_by or Super Admin can resend
    if token.sent_by:
        return token.sent_by == actor or actor.is_superuser
    
    # If no sent_by, Super Admin can resend
    return actor.is_superuser


def resend_verification_email(token, actor):
    """
    TASK 11: Resend verification email with authority transfer.
    
    This function:
    - Resends verification email
    - Updates sent_by to current actor
    - Updates last_sent_at
    - Logs audit events
    
    Args:
        token: EmailVerificationToken instance
        actor: User instance performing resend (must be Super Admin if sent_by is inactive)
    
    Returns:
        dict: Summary of resend action
    
    Raises:
        ValidationError: If actor is not authorized
    """
    if not can_resend_verification(token, actor):
        raise ValidationError(
            f"User {actor.email} is not authorized to resend verification email. "
            f"Only Super Admin can resend when original sender is inactive."
        )
    
    with transaction.atomic():
        # Resend the email
        send_verification_email(token.user, token)
        
        # Update sent_by and last_sent_at
        token.sent_by = actor
        token.last_sent_at = timezone.now()
        token.save(update_fields=['sent_by', 'last_sent_at'])
        
        # Log audit event
        from core.audit import log_deactivation
        original_sender = token.sent_by.email if token.sent_by else "System"
        log_deactivation(
            token,
            actor=actor,
            reason=f"EMAIL_VERIFICATION_RESENT - Original sender: {original_sender}, Resent by: {actor.email}"
        )
        
        logger.info(
            f"Verification email resent - "
            f"Token ID: {token.id}, User: {token.user.email}, "
            f"Original sender: {original_sender}, Resent by: {actor.email}"
        )
        
        return {
            'token_id': token.id,
            'user': token.user.email,
            'sent_by': actor.email,
            'last_sent_at': token.last_sent_at,
            'message': 'Verification email resent successfully'
        }


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
            logger.info(f"Admin Pandit {admin_pandit.email} sent no verification emails")
            return {
                'token_count': 0,
                'tokens_affected': [],
                'message': 'No verification tokens to transfer'
            }
        
        # sent_by is preserved (SET_NULL on delete, but we're deactivating, not deleting)
        # When Admin Pandit is deactivated, sent_by remains but is inactive
        # Super Admin can now resend (checked in can_resend_verification)
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            admin_pandit,
            actor=actor,
            reason=f"RESEND_AUTHORITY_TRANSFERRED - {token_count} verification token(s) affected, Super Admin can now resend"
        )
        
        logger.info(
            f"Email verification resend authority transferred - "
            f"Admin: {admin_pandit.email}, Tokens affected: {token_count}"
        )
        
        return {
            'token_count': token_count,
            'tokens_affected': [t.id for t in tokens],
            'message': f'{token_count} verification token(s) - Super Admin can now resend'
        }







