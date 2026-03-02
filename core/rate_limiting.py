"""
Generic rate limiting for API create endpoints.

Cache-based; limits by IP and by authenticated user.
Used for booking intent create, review create, etc.
"""

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from functools import wraps

# Booking intent create: 5 per 15 minutes per IP / per user
_DEFAULT_BOOKING_INTENT_ATTEMPTS = 5
_DEFAULT_BOOKING_INTENT_WINDOW = 900  # 15 minutes

# Review create: 5 per hour per user
_DEFAULT_REVIEW_CREATE_ATTEMPTS = 5
_DEFAULT_REVIEW_CREATE_WINDOW = 3600  # 1 hour


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def rate_limit_create(
    key_prefix,
    max_attempts=None,
    window_seconds=None,
    max_attempts_setting=None,
    window_setting=None,
    default_max=5,
    default_window=900,
):
    """
    Decorator: rate limit by IP and by authenticated user.
    Returns 429 with consistent JSON if limit exceeded.
    """
    _max = max_attempts if max_attempts is not None else getattr(
        settings, max_attempts_setting or 'RATE_LIMIT_CREATE_ATTEMPTS', default_max
    )
    _window = window_seconds if window_seconds is not None else getattr(
        settings, window_setting or 'RATE_LIMIT_CREATE_WINDOW', default_window
    )

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)

            ip = _get_client_ip(request)
            ip_key = f'{key_prefix}_ip_{ip}'
            ip_count = cache.get(ip_key, 0)
            if ip_count >= _max:
                return JsonResponse({
                    'error': 'Too many requests. Please try again later.',
                    'message': 'Rate limit exceeded. Please wait before trying again.',
                }, status=429)

            user_key = None
            if request.user.is_authenticated:
                user_key = f'{key_prefix}_user_{request.user.id}'
                user_count = cache.get(user_key, 0)
                if user_count >= _max:
                    return JsonResponse({
                        'error': 'Too many requests. Please try again later.',
                        'message': 'Rate limit exceeded. Please wait before trying again.',
                    }, status=429)

            # Increment before calling view (count this attempt)
            cache.set(ip_key, ip_count + 1, _window)
            if user_key:
                user_count = cache.get(user_key, 0)
                cache.set(user_key, user_count + 1, _window)

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def rate_limit_booking_intent_create(view_func):
    """Rate limit booking intent creation: 5 per 15 minutes per IP / per user."""
    return rate_limit_create(
        'booking_intent_create',
        max_attempts=5,
        window_seconds=900,
        default_max=5,
        default_window=900,
    )(view_func)


def rate_limit_review_create(view_func):
    """Rate limit review creation: 5 per hour per user (and per IP for anonymous)."""
    return rate_limit_create(
        'review_create',
        max_attempts=5,
        window_seconds=3600,
        default_max=5,
        default_window=3600,
    )(view_func)
