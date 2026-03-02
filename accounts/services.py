"""
Account Services (TASK 2: Email Verification Resend Service)

This module contains service functions for account management operations.
All business logic is centralized here, separate from views.
"""

import logging
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import User
from .email_verification import create_email_verification

logger = logging.getLogger(__name__)


class VerificationAlreadyCompleted(ValidationError):
    """Raised when trying to resend verification for already verified user."""
    pass


class CooldownNotElapsed(ValidationError):
    """Raised when resend is attempted before cooldown period."""
    pass


def resend_verification_email(user, requested_by=None):
    """
    Resends verification email if:
    - user is Pandit
    - user.email_verified is False (or email_verified_at is None)
    - last email was sent more than 30 seconds ago
    
    TASK 2: Email Verification Resend Service
    
    Args:
        user: User instance (Pandit) to resend verification for
        requested_by: User instance who requested the resend (for audit logging)
        
    Returns:
        EmailVerificationToken: Created verification token
        
    Raises:
        VerificationAlreadyCompleted: If user is already verified
        CooldownNotElapsed: If resend attempted within 30 seconds
        ValidationError: If user is not a Pandit or other validation fails
    """
    if not user or not isinstance(user, User):
        raise ValidationError("Valid user instance required")
    
    # Only Pandits need email verification
    if user.role != 'pandit':
        raise ValidationError("Email verification resend is only available for Pandit accounts")
    
    # Check if already verified
    if user.email_verified or user.email_verified_at:
        raise VerificationAlreadyCompleted("User email is already verified")
    
    # Enforce 30-second cooldown
    if user.last_verification_email_sent_at:
        time_since_last = timezone.now() - user.last_verification_email_sent_at
        if time_since_last < timedelta(seconds=30):
            remaining_seconds = 30 - int(time_since_last.total_seconds())
            raise CooldownNotElapsed(
                f"Please wait {remaining_seconds} seconds before requesting another verification email"
            )
    
    # Optional: Enforce max attempts per day (5 attempts)
    # Count attempts in last 24 hours for this specific user
    one_day_ago = timezone.now() - timedelta(days=1)
    if user.last_verification_email_sent_at and user.last_verification_email_sent_at >= one_day_ago:
        # Check how many times this user has requested resend in the last 24 hours
        # We'll use a simple approach: if last_verification_email_sent_at is recent, count tokens created
        from .models import EmailVerificationToken
        recent_tokens = EmailVerificationToken.objects.filter(
            user=user,
            created_at__gte=one_day_ago
        ).count()
        
        if recent_tokens >= 5:
            raise ValidationError("Maximum verification email attempts reached. Please try again tomorrow.")
    
    try:
        with transaction.atomic():
            # Update last_verification_email_sent_at before sending
            user.last_verification_email_sent_at = timezone.now()
            user.save(update_fields=['last_verification_email_sent_at'])
            
            # TASK 3: Log resend execution clearly
            logger.info(f"[EMAIL RESEND] Resending verification email for {user.email}")
            logger.info(f"[EMAIL RESEND] Requested by: {requested_by.email if requested_by else 'self'}")
            
            # Create and send verification email (reuses existing logic)
            # This will use the same corrected FROM address
            verification_token = create_email_verification(user)
            
            logger.info(f"[EMAIL RESEND] ✓ Verification email resent successfully for {user.email}")
            
            # TASK 7: Audit logging
            try:
                from analytics.audit_events import log_audit_event
                from referrals.constants import AUDIT_ACTION_EMAIL_VERIFICATION_SENT
                log_audit_event(
                    event_type=AUDIT_ACTION_EMAIL_VERIFICATION_SENT,
                    user=requested_by or user,
                    metadata={
                        'action': 'resend_verification',
                        'target_user_id': user.id,
                        'target_user_email': user.email,
                        'token_id': verification_token.public_id,
                        'result': 'sent',
                        'requested_by': requested_by.email if requested_by else user.email,
                    }
                )
            except Exception as audit_error:
                # Audit logging is optional, don't fail the operation
                logger.warning(f"Failed to log audit event for resend verification: {audit_error}")
            
            logger.info(
                f"Verification email resent for user {user.email} "
                f"(requested by: {requested_by.email if requested_by else 'self'})"
            )
            
            return verification_token
            
    except Exception as e:
        # Log error but re-raise for view to handle
        logger.error(
            f"Error resending verification email for user {user.email}: {str(e)}",
            exc_info=True
        )
        raise

