"""
Middleware for validating user sessions and forcing logout for deactivated users.

TASK 18: Login Sessions of Deactivated Users

This middleware ensures that:
- Deactivated users cannot remain logged in
- Session is invalidated on next request
- Graceful UX message shown
- No sudden crash or silent failure
"""

import logging
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger(__name__)


class SessionValidationMiddleware:
    """
    TASK 18: Middleware to force logout for deactivated users.
    
    On every authenticated request:
    - Check user.status
    - If status != ACTIVE or is_active=False:
        - Logout user
        - Clear session
        - Redirect to login with message
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip for anonymous users
        if request.user.is_authenticated:
            user = request.user
            
            # TASK 18: Check if user is deactivated or inactive
            # Allow 'pending' status (email verification pending, but not deactivated)
            # Block 'deactivated' and inactive accounts
            is_deactivated = (
                not user.is_active or
                user.status == 'deactivated' or
                (hasattr(user, 'status') and user.status == 'rejected')
            )
            
            if is_deactivated:
                # Log the forced logout
                logger.warning(
                    f"Forced logout for deactivated user - "
                    f"User: {user.email} (ID: {user.id}), "
                    f"Is Active: {user.is_active}, "
                    f"Status: {user.status}, "
                    f"Path: {request.path}"
                )
                
                # Log audit event
                try:
                    from core.audit import log_deactivation
                    log_deactivation(
                        user,
                        actor=None,
                        reason="SESSION_INVALIDATED - Account deactivated, session terminated"
                    )
                except Exception:
                    pass
                
                # Logout user and clear session
                logout(request)
                
                # Add message for user
                messages.error(
                    request,
                    'Your account has been deactivated. Please contact support to reactivate your account.'
                )
                
                # Redirect to login
                login_url = reverse('accounts:login')
                return redirect(f"{login_url}?next={request.path}")
        
        response = self.get_response(request)
        return response

