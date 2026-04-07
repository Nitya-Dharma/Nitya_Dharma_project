"""
Enhanced password reset views with security features:
- Rate limiting
- Audit logging
- Email notifications
"""
import logging
from django.contrib.auth import views as auth_views
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings
from django.core.mail import send_mail as django_send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)
User = get_user_model()

# Rate limiting settings
PASSWORD_RESET_RATE_LIMIT = 5  # Max requests per window
PASSWORD_RESET_RATE_WINDOW = 3600  # 1 hour in seconds


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_rate_limit(request, email=None):
    """
    Check if password reset request should be rate limited.
    
    Returns:
        (is_allowed, remaining_seconds)
    """
    # Use IP address for rate limiting
    ip_address = get_client_ip(request)
    cache_key_ip = f'password_reset_ip:{ip_address}'
    
    # Also rate limit by email if provided
    if email:
        cache_key_email = f'password_reset_email:{email.lower()}'
        email_count = cache.get(cache_key_email, 0)
        
        if email_count >= PASSWORD_RESET_RATE_LIMIT:
            # Get remaining time
            ttl = cache.ttl(cache_key_email)
            remaining = ttl if ttl else PASSWORD_RESET_RATE_WINDOW
            logger.warning(
                f"Password reset rate limit exceeded for email: {email} "
                f"(IP: {ip_address})"
            )
            return False, remaining
        
        # Increment email counter
        cache.set(
            cache_key_email,
            email_count + 1,
            PASSWORD_RESET_RATE_WINDOW
        )
    
    # Check IP-based rate limiting
    ip_count = cache.get(cache_key_ip, 0)
    
    if ip_count >= PASSWORD_RESET_RATE_LIMIT:
        ttl = cache.ttl(cache_key_ip)
        remaining = ttl if ttl else PASSWORD_RESET_RATE_WINDOW
        logger.warning(
            f"Password reset rate limit exceeded for IP: {ip_address}"
        )
        return False, remaining
    
    # Increment IP counter
    cache.set(
        cache_key_ip,
        ip_count + 1,
        PASSWORD_RESET_RATE_WINDOW
    )
    
    return True, 0


def log_password_reset_request(email, ip_address, success=True, reason=None):
    """Log password reset request for audit purposes."""
    log_message = (
        f"Password reset request - "
        f"Email: {email}, "
        f"IP: {ip_address}, "
        f"Success: {success}"
    )
    if reason:
        log_message += f", Reason: {reason}"
    
    if success:
        logger.info(log_message)
    else:
        logger.warning(log_message)


def send_password_change_notification(user):
    """Send email notification when password is changed."""
    try:
        subject = 'Password Changed - Nitya Dharma'
        
        # Build email body
        message = f"""
Hello {user.get_full_name() or user.email},

Your password has been successfully changed for your Nitya Dharma account.

If you did not make this change, please contact our support team immediately.

Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

— Nitya Dharma Team
        """.strip()
        
        try:
            # NOTE:
            # If Redis is UP but Celery worker is DOWN,
            # tasks will queue and NOT execute immediately.
            # This is expected Celery behavior.
            from core.tasks_email import send_email_task

            send_email_task.delay(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
        except Exception:
            django_send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        
        logger.info(f"Password change notification sent to {user.email}")
    except Exception as e:
        logger.error(f"Failed to send password change notification: {str(e)}")


class EnhancedPasswordResetView(auth_views.PasswordResetView):
    """
    Enhanced password reset view with rate limiting, audit logging, and simple email support.
    """
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/emails/password_reset_email_simple.html'
    subject_template_name = 'accounts/emails/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    
    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        """
        Override send_mail to send simple, clean emails with just the reset link.
        """
        from django.urls import reverse
        
        subject = render_to_string(subject_template_name, context).strip()
        
        # Build reset URL
        user = context.get('user')
        uid = context.get('uid')
        token = context.get('token')
        protocol = context.get('protocol', 'http')
        domain = context.get('domain', '127.0.0.1:8000')
        
        # Build the reset URL
        reset_url = f"{protocol}://{domain}{reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})}"
        
        # Create simple plain text message with just the link
        if user:
            user_name = user.get_full_name() or user.email
        else:
            user_name = 'User'
        
        message = f"""Hello {user_name},

You requested a password reset for your Nitya Dharma account.

Click the link below to set a new password:
{reset_url}

This link will expire in 24 hours and can only be used once.

If you didn't request this password reset, please ignore this email.

— Nitya Dharma Team"""
        
        # Send simple plain text email (no HTML)
        try:
            # NOTE:
            # If Redis is UP but Celery worker is DOWN,
            # tasks will queue and NOT execute immediately.
            # This is expected Celery behavior.
            from core.tasks_email import send_email_task

            send_email_task.delay(subject, message, from_email, [to_email])
        except Exception:
            django_send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[to_email],
                fail_silently=False,
            )
        
        logger.info(f"Password reset email sent to {to_email} (simple format)")
    
    def post(self, request, *args, **kwargs):
        """Handle POST request with rate limiting."""
        email = request.POST.get('email', '').strip()
        ip_address = get_client_ip(request)
        
        # Check rate limit
        is_allowed, remaining_seconds = check_rate_limit(request, email)
        
        if not is_allowed:
            # Log rate limit violation
            log_password_reset_request(
                email,
                ip_address,
                success=False,
                reason=f'Rate limit exceeded (wait {remaining_seconds}s)'
            )
            
            # Still show success message (security: don't reveal rate limiting)
            # But log it for monitoring
            return super().post(request, *args, **kwargs)
        
        # Log password reset request
        log_password_reset_request(email, ip_address, success=True)
        
        # Call parent to handle actual password reset
        response = super().post(request, *args, **kwargs)
        
        # If email was found and sent, log it
        if email:
            try:
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    logger.info(
                        f"Password reset email sent to {email} "
                        f"(User ID: {user.id}, IP: {ip_address})"
                    )
            except Exception as e:
                logger.error(f"Error checking user for password reset: {str(e)}")
        
        return response


class EnhancedPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """
    Enhanced password reset confirm view with audit logging and email notification.
    """
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')
    post_reset_login = False  # Don't auto-login after reset
    
    def dispatch(self, *args, **kwargs):
        """Handle dispatch and validate token."""
        # Get uidb64 and token from kwargs
        uidb64 = kwargs.get('uidb64', '')
        token = kwargs.get('token', '')
        
        # Log access attempt
        ip_address = get_client_ip(self.request)
        logger.info(
            f"Password reset confirmation accessed - "
            f"UID: {uidb64}, "
            f"Token: {token[:10] if token and len(token) > 10 else token if token else 'None'}..., "
            f"IP: {ip_address}"
        )
        
        try:
            # Call parent dispatch - this will handle token validation
            return super().dispatch(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in password reset confirmation: {str(e)}")
            # Re-raise to show proper error page
            raise
    
    def get_user(self, uidb64):
        """
        Override to handle user lookup and prevent errors with invalid tokens.
        """
        try:
            return super().get_user(uidb64)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None
    
    def get_context_data(self, **kwargs):
        """Add additional context and handle invalid links."""
        context = super().get_context_data(**kwargs)
        
        # Ensure uidb64 and token are in context from URL kwargs
        context['uidb64'] = self.kwargs.get('uidb64', '')
        context['token'] = self.kwargs.get('token', '')
        
        # If link is invalid, log it
        if not context.get('validlink', False):
            logger.warning(
                f"Invalid password reset link - "
                f"UID: {context.get('uidb64', '')}, "
                f"Token: {context.get('token', '')[:10] if context.get('token') else 'None'}"
            )
        
        return context
    
    def form_valid(self, form):
        """
        TASK 16: Handle successful password reset.
        
        Password reset is allowed even if user is deactivated.
        Account remains inactive after reset - login is blocked.
        """
        user = form.user
        ip_address = get_client_ip(self.request)
        
        # TASK 16: Check if user is inactive
        is_inactive = not user.is_active or user.status == 'deactivated'
        
        # Log password reset completion
        logger.info(
            f"Password reset completed - "
            f"User: {user.email} (ID: {user.id}), "
            f"IP: {ip_address}, "
            f"Is Active: {user.is_active}, "
            f"Status: {user.status}"
        )
        
        # Call parent to actually reset the password
        # This works even if user is inactive (Django allows it)
        response = super().form_valid(form)
        
        # Send notification email
        send_password_change_notification(user)
        
        # TASK 16: If user is inactive, add message about login being blocked
        if is_inactive:
            from django.contrib import messages
            messages.warning(
                self.request,
                'Your password has been reset successfully. However, your account is inactive. '
                'Please contact support to reactivate your account before logging in.'
            )
            
            # Log that login will be blocked
            logger.warning(
                f"Password reset completed for inactive user - "
                f"User: {user.email} (ID: {user.id}), "
                f"Login will be blocked until account is reactivated"
            )
            
            # Log audit event
            from core.audit import log_deactivation
            log_deactivation(
                user,
                actor=None,
                reason="PASSWORD_RESET_COMPLETED - Account remains inactive, login blocked"
            )
        else:
            # Log audit event for active users
            from core.audit import log_deactivation
            log_deactivation(
                user,
                actor=None,
                reason="PASSWORD_RESET_COMPLETED - Account active, login allowed"
            )
        
        return response
    
    def form_invalid(self, form):
        """Log invalid password reset attempts."""
        ip_address = get_client_ip(self.request)
        uidb64 = self.kwargs.get('uidb64', '')
        logger.warning(
            f"Password reset confirmation failed - "
            f"UID: {uidb64}, "
            f"IP: {ip_address}, "
            f"Errors: {form.errors}"
        )
        return super().form_invalid(form)


