"""
Views for email verification resend functionality.

TASK 3: Email Verification Resend View
"""

import logging
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from .models import User
from .services import (
    resend_verification_email,
    VerificationAlreadyCompleted,
    CooldownNotElapsed,
    RESEND_UNAUTHORIZED,
)
from .services_email_verification_authority import (
    authoritative_verification_token,
    can_resend_verification,
)
from .utils import is_admin, is_pandit

logger = logging.getLogger(__name__)

PERMISSION_DENIED = (
    "You do not have permission to resend verification email for this account."
)


def _validation_text(exc):
    messages_list = getattr(exc, "messages", None)
    if messages_list:
        return " ".join(str(message) for message in messages_list)
    return str(exc)


@login_required
@require_POST
@csrf_protect
def resend_pandit_verification(request, pandit_public_id):
    """
    Resend email verification for a Pandit account.
    
    TASK 3: Email Verification Resend View
    
    Authorization:
    - Pandit → own account only, and self-service does not record a sender
    - Admin Pandit → may establish a null sender, or resend while that same sender is active
    - A different Admin Pandit cannot take over an existing or inactive sender
    - Super Admin → may resend, including after the original sender is inactive,
      without replacing an existing sender
    
    Args:
        request: HTTP request object
        pandit_public_id: Public ID (UUID) of the Pandit to resend verification for
        
    Returns:
        Redirect to appropriate dashboard with success/error message
    """
    try:
        # Resolve Pandit by public_id
        target_pandit = get_object_or_404(User, public_id=pandit_public_id, role='pandit')
        
        requester = request.user
        current_token = authoritative_verification_token(target_pandit)
        if not can_resend_verification(
            current_token,
            requester,
            target_user=target_pandit,
        ):
            messages.error(request, PERMISSION_DENIED)
            if is_pandit(requester):
                return redirect('module5_dashboards:dashboard_pandit')
            elif is_admin(requester):
                return redirect('module5_dashboards:dashboard_admin_pandit')
            else:
                return redirect('core:home')
        
        # Call service function to resend verification email
        try:
            verification_token = resend_verification_email(
                user=target_pandit,
                requested_by=requester
            )
            
            # Success message
            if requester.id == target_pandit.id:
                messages.success(
                    request,
                    'Verification email has been sent. Please check your inbox (and spam folder).'
                )
            else:
                messages.success(
                    request,
                    f'Verification email has been sent to {target_pandit.email}.'
                )
            
        except VerificationAlreadyCompleted:
            messages.info(
                request,
                'This account is already verified. No action needed.'
            )
        except CooldownNotElapsed as e:
            messages.warning(
                request,
                str(e)
            )
        except ValidationError as exc:
            text = _validation_text(exc)
            if text == RESEND_UNAUTHORIZED:
                messages.error(request, PERMISSION_DENIED)
            else:
                messages.error(request, text)
        except Exception as exc:
            logger.error(
                "Error resending Pandit verification email",
                extra={"error_type": type(exc).__name__},
            )
            messages.error(
                request,
                "Failed to send verification email. Please try again later."
            )
        
        # Redirect based on requester role
        if is_pandit(requester) and requester.id == target_pandit.id:
            # Pandit viewing own dashboard
            return redirect('module5_dashboards:dashboard_pandit')
        elif is_admin(requester):
            # Admin Pandit viewing admin dashboard
            return redirect('module5_dashboards:dashboard_admin_pandit')
        elif requester.is_superuser:
            # Super Admin viewing super admin dashboard
            return redirect('module5_dashboards:dashboard_super_admin')
        else:
            return redirect('core:home')
            
    except User.DoesNotExist:
        messages.error(request, 'Pandit account not found.')
        return redirect('core:home')
    except Exception as exc:
        logger.error(
            "Unexpected error in resend_pandit_verification",
            extra={"error_type": type(exc).__name__},
        )
        messages.error(request, 'An unexpected error occurred. Please try again.')
        return redirect('core:home')

