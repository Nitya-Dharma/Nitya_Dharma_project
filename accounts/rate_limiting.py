"""
Rate limiting utilities for authentication endpoints.

This module provides simple rate limiting to prevent brute-force attacks.
"""

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from functools import wraps
import time

# Defaults preserved for identical behavior when settings are missing
_DEFAULT_LOGIN_ATTEMPTS = 5
_DEFAULT_LOGIN_WINDOW_SECONDS = 300


def rate_limit_login(max_attempts=None, window_seconds=None, key_prefix='login_attempt'):
    """
    Rate limiting decorator for login endpoints.
    
    SECURITY FIX: Prevents brute-force attacks by limiting login attempts.
    
    Args:
        max_attempts: Maximum number of failed attempts allowed (default: 5)
        window_seconds: Time window in seconds (default: 5 minutes)
        key_prefix: Cache key prefix
    
    Usage:
        @rate_limit_login(max_attempts=5, window_seconds=300)
        def login_view(request):
            # Login logic
    """
    # Safe settings override: optional; missing => same behavior as before
    _max = max_attempts if max_attempts is not None else getattr(
        settings, 'LOGIN_RATE_LIMIT_ATTEMPTS', _DEFAULT_LOGIN_ATTEMPTS
    )
    _window = window_seconds if window_seconds is not None else getattr(
        settings, 'LOGIN_RATE_LIMIT_WINDOW_SECONDS', _DEFAULT_LOGIN_WINDOW_SECONDS
    )

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Only apply rate limiting to POST requests
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)
            
            # Get client identifier (IP address)
            ip_address = request.META.get('REMOTE_ADDR', 'unknown')
            # Get email from POST or JSON body
            if request.content_type == 'application/json':
                import json
                try:
                    data = json.loads(request.body) if request.body else {}
                    email = data.get('email', '').strip()
                except:
                    email = ''
            else:
                email = request.POST.get('email', '').strip()
            
            # Create cache keys
            ip_key = f'{key_prefix}_ip_{ip_address}'
            email_key = f'{key_prefix}_email_{email}' if email else None
            
            # Check IP-based rate limit
            ip_attempts = cache.get(ip_key, 0)
            if ip_attempts >= _max:
                if request.content_type == 'application/json':
                    return JsonResponse({
                        'error': 'Too many login attempts. Please try again later.',
                        'message': 'Rate limit exceeded. Please wait before trying again.'
                    }, status=429)
                from django.contrib import messages
                from django.shortcuts import render
                messages.error(request, 'Too many login attempts. Please try again later.')
                return render(request, 'accounts/login.html', {'rate_limited': True})
            
            # Check email-based rate limit (if email provided)
            if email_key:
                email_attempts = cache.get(email_key, 0)
                if email_attempts >= _max:
                    if request.content_type == 'application/json':
                        return JsonResponse({
                            'error': 'Too many login attempts for this email. Please try again later.',
                            'message': 'Rate limit exceeded. Please wait before trying again.'
                        }, status=429)
                    from django.contrib import messages
                    from django.shortcuts import render
                    messages.error(request, 'Too many login attempts for this email. Please try again later.')
                    return render(request, 'accounts/login.html', {'email': email, 'rate_limited': True})
            
            # Store initial auth state
            was_authenticated_before = hasattr(request, 'user') and request.user.is_authenticated
            
            # Call the view
            response = view_func(request, *args, **kwargs)
            
            # Check if login was successful
            # Success indicators:
            # 1. User is now authenticated (wasn't before)
            # 2. Response is a redirect (302/301) - typical for successful login
            is_authenticated_after = hasattr(request, 'user') and request.user.is_authenticated
            is_redirect = response.status_code in [302, 301]
            
            if not was_authenticated_before and (is_authenticated_after or is_redirect):
                # Login successful - reset counters
                cache.delete(ip_key)
                if email_key:
                    cache.delete(email_key)
            elif not was_authenticated_before and not is_authenticated_after:
                # Login failed - increment counters
                cache.set(ip_key, ip_attempts + 1, _window)
                if email_key:
                    cache.set(email_key, email_attempts + 1, _window)
            
            return response
        return _wrapped_view
    return decorator

