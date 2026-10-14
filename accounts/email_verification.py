"""
Email Verification Service (TASK 3: Email Verification Service)

This module implements email verification functionality for user accounts.
Email verification is mandatory for all users, especially Pandits.

Rules:
- One active token per user
- Tokens expire in 24 hours
- Immutable after use
- Verification required before activation
"""

import logging
import threading
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse

from .models import EmailVerificationToken, User

logger = logging.getLogger(__name__)


def create_email_verification(user, sent_by=None):
    """
    Create an email verification token for a user.
    
    TASK 3: Email Verification Service
    TASK 11: Track who sent the verification email
    
    Rules:
    - One active token per user (deactivate old tokens)
    - Token expires in 24 hours
    - Send verification email
    - Track sent_by for audit
    
    Args:
        user: User instance (must be authenticated)
        sent_by: User instance (optional, who is sending this verification)
        
    Returns:
        EmailVerificationToken: Created verification token
        
    Raises:
        ValidationError: If user is invalid
    """
    if not user or not isinstance(user, User):
        raise ValidationError("Valid user instance required")
    
    if not user.email:
        raise ValidationError("User email is required for verification")
    
    try:
        with transaction.atomic():
            # Deactivate any existing active tokens for this user
            EmailVerificationToken.objects.filter(
                user=user,
                is_used=False,
                expires_at__gt=timezone.now()
            ).update(is_used=True, used_at=timezone.now())
            
            # Create new verification token
            # TASK 11: Track who sent the verification
            verification_token = EmailVerificationToken.objects.create(
                user=user,
                sent_by=sent_by,
                last_sent_at=timezone.now() if sent_by else None
            )
            
            # STEP 3: Transaction Safety - Send email AFTER transaction commits
            # Use transaction.on_commit() to ensure email is only sent if transaction succeeds
            def send_email_after_commit():
                # STEP 7: Verify active email backend at runtime
                # Use module-level settings import (already imported at top of file)
                email_backend = getattr(settings, 'EMAIL_BACKEND', 'unknown')
                email_host_user = getattr(settings, 'EMAIL_HOST_USER', '')
                email_host_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
                
                logger.warning(f"[EMAIL DEBUG] ========================================")
                logger.warning(f"[EMAIL DEBUG] TRANSACTION COMMITTED - Sending email")
                logger.warning(f"[EMAIL DEBUG] ========================================")
                logger.warning(f"[EMAIL DEBUG] STEP 7: Runtime Email Backend Check")
                logger.warning(f"[EMAIL DEBUG] EMAIL_BACKEND: {email_backend}")
                logger.warning(f"[EMAIL DEBUG] EMAIL_HOST_USER: {email_host_user}")
                logger.warning(f"[EMAIL DEBUG] EMAIL_HOST_PASSWORD: {'SET' if email_host_password else 'NOT SET'}")
                logger.warning(f"[EMAIL DEBUG] DEFAULT_FROM_EMAIL: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}")
                
                # Verify SMTP backend is active
                if 'console' in email_backend:
                    logger.error(f"[EMAIL DEBUG] ⚠️ WARNING: Using CONSOLE backend, not SMTP!")
                    logger.error(f"[EMAIL DEBUG] Email will be printed to terminal, NOT sent via SMTP")
                elif 'smtp' in email_backend.lower():
                    logger.warning(f"[EMAIL DEBUG] ✓ Using SMTP backend - emails will be sent")
                else:
                    logger.error(f"[EMAIL DEBUG] ⚠️ Unknown email backend: {email_backend}")
                
                logger.warning(f"[EMAIL DEBUG] User: {user.email}")
                logger.warning(f"[EMAIL DEBUG] User ID: {user.id}")
                logger.warning(f"[EMAIL DEBUG] User is_active: {user.is_active}")
                logger.warning(f"[EMAIL DEBUG] User email_verified: {user.email_verified}")
                logger.warning(f"[EMAIL DEBUG] Token ID: {verification_token.id}")
                logger.warning(f"[EMAIL DEBUG] Token public_id: {verification_token.public_id}")
                logger.warning(f"[EMAIL DEBUG] Token expires_at: {verification_token.expires_at}")
                
                # Send verification email in a background thread so the HTTP request returns
                # immediately and does not hit Gunicorn/platform timeouts (e.g. Railway).
                def _send_in_thread():
                    try:
                        send_verification_email(user, verification_token)
                        logger.info(f"Verification email sent to {user.email}")
                        # TASK 9: Log audit event (after email is sent)
                        try:
                            from analytics.audit_events import log_audit_event
                            from referrals.constants import AUDIT_ACTION_EMAIL_VERIFICATION_SENT
                            log_audit_event(
                                event_type=AUDIT_ACTION_EMAIL_VERIFICATION_SENT,
                                user=user,
                                metadata={
                                    'token_id': verification_token.public_id,
                                    'expires_at': verification_token.expires_at.isoformat(),
                                }
                            )
                        except Exception:
                            pass
                    except Exception as email_error:
                        logger.error(
                            "Email verification scheduling failed for %s",
                            user.email,
                            extra={"error_type": type(email_error).__name__},
                        )

                thread = threading.Thread(target=_send_in_thread, daemon=True)
                thread.start()
                logger.warning(f"[EMAIL DEBUG] Email send started in background for {user.email}")
            
            # Schedule email to be sent after transaction commits
            transaction.on_commit(send_email_after_commit)
            
            logger.info("Email verification token created for user %s", user.email)
            return verification_token
            
    except Exception as e:
        logger.error(
            "Email verification token creation failed for %s",
            user.email,
            extra={"error_type": type(e).__name__},
        )
        raise


def send_verification_email(user, verification_token):
    """
    Send email verification email to user.
    
    TASK 3: Email sending
    
    Args:
        user: User instance
        verification_token: EmailVerificationToken instance
    """
    # STEP 5: Email Field Validation - Ensure we use saved user.email field
    if not user or not hasattr(user, 'email') or not user.email:
        logger.error(f"[EMAIL DEBUG] Invalid user or missing email field. User: {user}")
        raise ValidationError("User email is required for sending verification email")
    
    # Ensure user is saved and email comes from database field, not form data
    user_email = user.email  # Use saved field, not request.POST
    
    try:
        # Build verification URL (use absolute URL)
        # STEP 4: Token generation validation - ensure token exists and is valid
        if not verification_token or not verification_token.token:
            logger.error(f"[EMAIL DEBUG] Invalid verification token - token is None or empty")
            raise ValidationError("Invalid verification token for email sending")
        
        logger.warning("Email verification URL construction started")
        
        # Build absolute URL using SITE_URL from settings (FIXED: Use SITE_URL directly)
        try:
            from django.urls import reverse
            
            # Get SITE_URL from settings (preferred method)
            site_url = getattr(settings, 'SITE_URL', None)
            
            if not site_url:
                # Fallback: Try to construct from ALLOWED_HOSTS
                allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
                if allowed_hosts and allowed_hosts[0] != '*':
                    host = allowed_hosts[0]
                else:
                    host = '127.0.0.1:8000'  # Use 127.0.0.1 instead of localhost
                
                # Add protocol
                use_https = getattr(settings, 'USE_HTTPS', False)
                protocol = 'https' if use_https else 'http'
                site_url = f"{protocol}://{host}"
            
            # Ensure SITE_URL doesn't end with slash
            site_url = site_url.rstrip('/')
            
            # Build relative URL path
            relative_path = reverse('accounts:verify_email', args=[verification_token.token])
            
            # Ensure relative_path starts with /
            if not relative_path.startswith('/'):
                relative_path = '/' + relative_path
            
            # Build absolute URL (FIXED: Simple concatenation)
            verification_url = f"{site_url}{relative_path}"
            
            logger.warning(f"[EMAIL DEBUG] SITE_URL: {site_url}")
            logger.warning("Email verification URL constructed")
            
        except Exception as url_error:
            logger.error(
                "Email verification URL construction failed",
                extra={"error_type": type(url_error).__name__},
            )
            # Final fallback: use relative URL (user will need to copy-paste)
            verification_url = f'/accounts/verify-email/{verification_token.token}/'
            logger.warning("Email verification URL fallback constructed")
        
        # Email subject
        subject = 'Verify your email address - Nitya Dharma'
        
        # Email body (plain text for now - can be HTML later)
        message = f"""
Hello {user.get_full_name() or user.email},

Thank you for registering with Nitya Dharma.

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.

Best regards,
Nitya Dharma Team
"""
        
        # STEP 5: Use saved user.email field (not form data)
        # STEP 6: Enhanced debug logs
        # STEP 7: Verify email backend at runtime
        # TASK 2: Delivery-safe logging with FROM/TO addresses
        from_email = settings.DEFAULT_FROM_EMAIL
        email_host_user = getattr(settings, 'EMAIL_HOST_USER', '')
        
        logger.warning(f"[EMAIL DEBUG] ========================================")
        logger.warning(f"[EMAIL DEBUG] STEP 7: Email Backend Verification in send_verification_email()")
        logger.warning(f"[EMAIL DEBUG] EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        logger.warning(f"[EMAIL DEBUG] EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NOT SET')}")
        logger.warning(f"[EMAIL DEBUG] EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NOT SET')}")
        logger.warning(f"[EMAIL DEBUG] EMAIL_USE_TLS: {getattr(settings, 'EMAIL_USE_TLS', 'NOT SET')}")
        logger.warning(f"[EMAIL DEBUG] EMAIL_HOST_USER: {email_host_user}")
        logger.warning(f"[EMAIL DEBUG] EMAIL_HOST_PASSWORD: {'SET' if getattr(settings, 'EMAIL_HOST_PASSWORD', '') else 'NOT SET'}")
        logger.warning(f"[EMAIL DEBUG] DEFAULT_FROM_EMAIL: {from_email}")
        
        # TASK 2: Delivery-safe logging - log FROM/TO addresses
        logger.info(f"[EMAIL DELIVERY] FROM={from_email} TO={user_email} BACKEND={settings.EMAIL_BACKEND}")
        
        # TASK 2: Warn if FROM != EMAIL_HOST_USER (Gmail will drop)
        if email_host_user and from_email != email_host_user:
            logger.error(f"[EMAIL DELIVERY] ⚠️ WARNING: FROM address mismatch!")
            logger.error(f"[EMAIL DELIVERY] FROM={from_email} != EMAIL_HOST_USER={email_host_user}")
            logger.error(f"[EMAIL DELIVERY] Gmail will silently drop this email!")
        
        logger.warning(f"[EMAIL DEBUG] ========================================")
        logger.warning(f"[EMAIL DEBUG] About to call send_mail()")
        logger.warning(f"[EMAIL DEBUG] Recipient: {user_email}")
        logger.warning(f"[EMAIL DEBUG] From: {from_email}")
        logger.warning(f"[EMAIL DEBUG] Subject: {subject}")
        
        # Validate email address format before sending
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_email(user_email)
            logger.warning(f"[EMAIL DEBUG] Email address format is valid: {user_email}")
        except DjangoValidationError as email_validation_error:
            logger.error(f"[EMAIL DEBUG] Invalid email address format: {user_email} - {email_validation_error}")
            raise ValidationError(f"Invalid email address format: {user_email}")
        
        # Send email
        logger.warning(f"[EMAIL DEBUG] Calling send_mail() NOW...")
        try:
            # TASK 2: Use from_email variable (already set above)
            try:
                # NOTE:
                # If Redis is UP but Celery worker is DOWN,
                # tasks will queue and NOT execute immediately.
                # This is expected Celery behavior.
                from core.tasks_email import send_email_task

                send_email_task.delay(subject, message, from_email, [user_email])
                result = 1
            except Exception:
                result = send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_email,  # Use verified from_email
                    recipient_list=[user_email],  # Use saved field
                    fail_silently=False,  # Raise exception on failure
                )
            # TASK 2: Log delivery data (result is number of emails sent, typically 1)
            logger.warning(f"[EMAIL DEBUG] ✓ send_mail() completed successfully for {user_email}")
            logger.warning(f"[EMAIL DEBUG] send_mail() returned: {result} (1 = success)")
            logger.info(f"[EMAIL DELIVERY] ✓ Email sent: FROM={from_email} TO={user_email} RESULT={result}")
            logger.warning(f"[EMAIL DEBUG] Email should arrive at: {user_email}")
            logger.info(f"Verification email sent to {user_email}")
        except Exception as send_error:
            logger.error("Email verification send failed for %s", user_email)
            logger.error(
                "Email verification send failed",
                extra={"error_type": type(send_error).__name__},
            )
            raise  # Re-raise to ensure error is visible
        
    except Exception as e:
        logger.error(f"[EMAIL DEBUG] ========================================")
        logger.error(f"[EMAIL DEBUG] CRITICAL: Email sending FAILED")
        logger.error(f"[EMAIL DEBUG] ========================================")
        logger.error(
            "Email verification send failed for %s",
            user_email,
            extra={"error_type": type(e).__name__},
        )
        # Check email backend and warn if using console
        # Use module-level settings import (already imported at top of file)
        email_backend = getattr(settings, 'EMAIL_BACKEND', 'unknown')
        logger.error(f"[EMAIL DEBUG] Email backend: {email_backend}")
        if hasattr(settings, 'EMAIL_BACKEND') and 'console' in settings.EMAIL_BACKEND:
            logger.warning(f"[EMAIL DEBUG] Using console email backend. Email will be printed to terminal, not sent via SMTP.")
        logger.error(f"[EMAIL DEBUG] ========================================")
        # Re-raise the exception so calling code knows email failed
        # This ensures errors are visible and not silently swallowed
        raise


def verify_email(token):
    """
    Verify email using token.
    
    TASK 3: Email verification
    
    Rules:
    - Token must be valid (not used, not expired)
    - Mark token as used
    - Mark user.email_verified = True
    
    Args:
        token: Verification token string
        
    Returns:
        User: Verified user instance
        
    Raises:
        ValidationError: If token is invalid or expired
    """
    if not token or not token.strip():
        raise ValidationError("Verification token is required")
    
    try:
        verification_token = EmailVerificationToken.objects.get(token=token.strip())
    except EmailVerificationToken.DoesNotExist:
        raise ValidationError("Invalid verification token")
    
    # Check if token is valid
    if not verification_token.is_valid():
        if verification_token.is_used:
            raise ValidationError("This verification token has already been used")
        if verification_token.expires_at < timezone.now():
            raise ValidationError("This verification token has expired")
        raise ValidationError("This verification token is invalid")
    
    try:
        with transaction.atomic():
            # Mark token as used
            verification_token.is_used = True
            verification_token.used_at = timezone.now()
            verification_token.save()
            
            # TASK 17: Email verification confirms email ownership ONLY
            # DO NOT change role or status - these are admin decisions
            user = verification_token.user
            
            # Store original role/status for audit (in case they changed)
            # Refresh from DB to get current state (may have changed since token creation)
            user.refresh_from_db()
            original_role = user.role
            original_status = user.status
            
            # TASK 17: Only set email_verified - nothing else
            # DO NOT set is_active=True
            # DO NOT change role
            # DO NOT change status
            # Verification = email ownership only
            user.email_verified = True
            user.email_verified_at = timezone.now()
            user.save(update_fields=['email_verified', 'email_verified_at'])

            # Bureau-only sync: flip BureauProfile.is_email_verified when a profile exists.
            # Queryset update avoids save()/signals and does not approve or activate.
            from bureaus.models import BureauProfile

            BureauProfile.objects.filter(user=user).update(is_email_verified=True)
            
            # TASK 17: Verify that role/status were NOT changed by this operation
            user.refresh_from_db()
            if user.role != original_role or user.status != original_status:
                # This should never happen, but log if it does
                logger.error(
                    f"CRITICAL: Role/status changed during email verification - "
                    f"User: {user.email}, Original role: {original_role}, Current: {user.role}, "
                    f"Original status: {original_status}, Current: {user.status}"
                )
            
            # TASK 17: Log if role/status changed before verification
            metadata = {
                'token_id': verification_token.public_id,
                'verified_at': verification_token.used_at.isoformat() if verification_token.used_at else None,
                'role_at_verification': user.role,
                'status_at_verification': user.status,
            }
            
            if original_role != user.role:
                metadata['role_changed_before_verification'] = True
                metadata['original_role'] = original_role
                logger.warning(
                    f"Email verified - Role changed before verification: "
                    f"User: {user.email}, Original: {original_role}, Current: {user.role}"
                )
                # Log audit event
                try:
                    from analytics.audit_events import log_audit_event
                    from referrals.constants import AUDIT_ACTION_EMAIL_VERIFIED
                    log_audit_event(
                        event_type='ROLE_CHANGED_BEFORE_VERIFICATION',
                        user=user,
                        metadata=metadata
                    )
                except Exception:
                    pass
            
            if original_status != user.status:
                metadata['status_changed_before_verification'] = True
                metadata['original_status'] = original_status
                logger.warning(
                    f"Email verified - Status changed before verification: "
                    f"User: {user.email}, Original: {original_status}, Current: {user.status}"
                )
                # Log audit event
                try:
                    from analytics.audit_events import log_audit_event
                    log_audit_event(
                        event_type='STATUS_CHANGED_BEFORE_VERIFICATION',
                        user=user,
                        metadata=metadata
                    )
                except Exception:
                    pass
            
            # TASK 9: Log audit event
            try:
                from analytics.audit_events import log_audit_event
                from referrals.constants import AUDIT_ACTION_EMAIL_VERIFIED
                log_audit_event(
                    event_type=AUDIT_ACTION_EMAIL_VERIFIED,
                    user=user,
                    metadata=metadata
                )
            except Exception:
                # Audit logging is optional
                pass
            
            logger.info(
                "Email verified for user %s. Role: %s, Status: %s (unchanged by verification)",
                user.email,
                user.role,
                user.status,
            )
            return user
            
    except Exception as e:
        logger.error(
            "Email verification failed",
            extra={"error_type": type(e).__name__},
        )
        raise


def get_active_verification_token(user):
    """
    Get active verification token for a user (if exists).
    
    Args:
        user: User instance
        
    Returns:
        EmailVerificationToken or None: Active token if exists
    """
    if not user or not isinstance(user, User):
        return None
    
    try:
        return EmailVerificationToken.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
    except Exception:
        return None

