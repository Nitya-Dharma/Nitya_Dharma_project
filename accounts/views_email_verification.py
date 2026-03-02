"""
Email Verification Views (TASK 3: Email Verification)

This module contains views for email verification.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.core.exceptions import ValidationError
from .email_verification import verify_email

logger = logging.getLogger(__name__)


def verify_email_view(request, token):
    """
    Email verification view.
    
    TASK 3: Email verification view
    
    Args:
        request: HTTP request object
        token: Verification token from URL
        
    Returns:
        Redirect to login or error page
    """
    # Add logging at entry point
    logger.info(f"[VERIFY EMAIL] View hit - token: {token[:20]}... (length: {len(token) if token else 0})")
    
    if not token or not token.strip():
        logger.warning("[VERIFY EMAIL] Empty token provided")
        messages.error(request, 'Invalid verification link. Token is missing.')
        return redirect('accounts:login')
    
    # Clean token (remove any whitespace)
    token = token.strip()
    
    try:
        logger.info(f"[VERIFY EMAIL] Attempting to verify token: {token[:20]}...")
        user = verify_email(token)
        logger.info(f"[VERIFY EMAIL] ✓ Email verified successfully for user: {user.email}")
        
        # TASK 17: Check account status after verification
        # Verification confirms email only - role/status resolved at activation time
        if user.status == 'pending':
            messages.info(
                request,
                'Your email is verified. Your account is pending review by an Admin Pandit. '
                'You will be notified upon approval.'
            )
        elif user.status == 'deactivated':
            messages.warning(
                request,
                'Your email is verified. However, your account has been deactivated. '
                'Please contact support to reactivate your account.'
            )
        elif user.status == 'rejected':
            messages.warning(
                request,
                'Your email is verified. However, your account registration was rejected. '
                'Please contact support for more information.'
            )
        else:
            messages.success(request, f'Email verified successfully! You can now log in with {user.email}.')
        
        return redirect('accounts:login')
    except ValidationError as e:
        logger.warning(f"[VERIFY EMAIL] Validation error: {str(e)}")
        messages.error(request, f'Email verification failed: {str(e)}')
        return redirect('accounts:login')
    except Exception as e:
        logger.error(f"[VERIFY EMAIL] ✗ Unexpected error during verification: {str(e)}", exc_info=True)
        messages.error(request, f'Email verification failed: {str(e)}')
        return redirect('accounts:login')

