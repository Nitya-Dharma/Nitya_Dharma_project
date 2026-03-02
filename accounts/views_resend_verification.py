"""
Views for email verification resend functionality.

TASK 3: Email Verification Resend View
"""

import logging
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from .models import User
from .services import (
    resend_verification_email,
    VerificationAlreadyCompleted,
    CooldownNotElapsed
)
from .utils import is_admin, is_pandit

logger = logging.getLogger(__name__)


@login_required
@require_POST
@csrf_protect
def resend_pandit_verification(request, pandit_public_id):
    """
    Resend email verification for a Pandit account.
    
    TASK 3: Email Verification Resend View
    
    Authorization:
    - Pandit → can resend for self only
    - Admin Pandit → can resend for Pandits they oversee
    - Super Admin → can resend for any Pandit
    
    Args:
        request: HTTP request object
        pandit_public_id: Public ID (UUID) of the Pandit to resend verification for
        
    Returns:
        Redirect to appropriate dashboard with success/error message
    """
    try:
        # Resolve Pandit by public_id
        target_pandit = get_object_or_404(User, public_id=pandit_public_id, role='pandit')
        
        # Authorization checks
        requester = request.user
        
        # Case 1: Pandit requesting for self
        if is_pandit(requester) and requester.id == target_pandit.id:
            # Self-service: allowed
            pass
        # Case 2: Admin Pandit requesting for another Pandit
        elif is_admin(requester) and not requester.is_superuser:
            # Admin Pandit can resend for any Pandit (they oversee all Pandits)
            # No additional check needed - Admin Pandit has global Pandit management access
            pass
        # Case 3: Super Admin requesting for any Pandit
        elif requester.is_superuser:
            # Super Admin can resend for any Pandit
            pass
        else:
            # Unauthorized: Pandit trying to resend for another Pandit
            messages.error(
                request,
                'You do not have permission to resend verification email for this account.'
            )
            # Redirect based on role
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
        except Exception as e:
            logger.error(
                f"Error resending verification email for {target_pandit.email}: {str(e)}",
                exc_info=True
            )
            messages.error(
                request,
                f'Failed to send verification email: {str(e)}'
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
    except Exception as e:
        logger.error(
            f"Unexpected error in resend_pandit_verification: {str(e)}",
            exc_info=True
        )
        messages.error(request, 'An unexpected error occurred. Please try again.')
        return redirect('core:home')

