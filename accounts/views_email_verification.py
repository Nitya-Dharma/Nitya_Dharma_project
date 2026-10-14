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
    logger.info("Email verification attempted")
    
    if not token or not token.strip():
        logger.warning("Email verification rejected: empty token")
        messages.error(request, 'Invalid verification link. Token is missing.')
        return redirect('accounts:login')
    
    # Clean token (remove any whitespace)
    token = token.strip()
    
    try:
        user = verify_email(token)
        logger.info("Email verification succeeded for user %s", user.email)
        
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
        logger.warning("Email verification rejected")
        messages.error(request, 'This verification link is invalid or expired. Please request a new one.')
        return redirect('accounts:login')
    except Exception as e:
        logger.error(
            "Email verification failed",
            extra={"error_type": type(e).__name__},
        )
        messages.error(request, 'This verification link is invalid or expired. Please request a new one.')
        return redirect('accounts:login')

