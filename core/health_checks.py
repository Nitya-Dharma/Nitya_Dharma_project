"""
Health Checks — PART 5 — PRODUCTION READINESS

TASK 5.10: Health Checks

Lightweight system health checks for:
- DB connectivity
- Email backend
- Cache (if present)

App fails fast if critical dependency missing.
"""

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def check_database():
    """
    Check database connectivity.
    
    Returns:
        tuple: (is_healthy: bool, message: str)
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result[0] == 1:
                return True, "Database connection healthy"
            else:
                return False, "Database query returned unexpected result"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False, f"Database connection failed: {str(e)}"


def check_cache():
    """
    Check cache connectivity (if configured).
    
    Returns:
        tuple: (is_healthy: bool, message: str)
    """
    if not hasattr(settings, 'CACHES') or not settings.CACHES:
        return True, "Cache not configured (skipped)"
    
    try:
        # Try to set and get a test value
        test_key = 'health_check_test'
        test_value = 'test_value'
        cache.set(test_key, test_value, 10)
        retrieved = cache.get(test_key)
        
        if retrieved == test_value:
            cache.delete(test_key)
            return True, "Cache connection healthy"
        else:
            return False, "Cache returned unexpected value"
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return False, f"Cache connection failed: {str(e)}"


def check_email_backend():
    """
    Check email backend configuration.
    
    Returns:
        tuple: (is_healthy: bool, message: str)
    """
    if not hasattr(settings, 'EMAIL_BACKEND'):
        return True, "Email backend not configured (skipped)"
    
    try:
        # Check if email backend is configured
        email_backend = settings.EMAIL_BACKEND
        
        # For console backend, always healthy
        if email_backend == 'django.core.mail.backends.console.EmailBackend':
            return True, "Email backend configured (console)"
        
        # For SMTP, check settings exist
        if email_backend == 'django.core.mail.backends.smtp.EmailBackend':
            if hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST:
                return True, "Email backend configured (SMTP)"
            else:
                return False, "SMTP email backend configured but EMAIL_HOST not set"
        
        return True, f"Email backend configured ({email_backend})"
    except Exception as e:
        logger.error(f"Email backend health check failed: {e}")
        return False, f"Email backend check failed: {str(e)}"


def health_check(request):
    """
    Health check endpoint.
    
    GET /health/
    
    Returns:
        JSON response with health status
    """
    checks = {
        'database': check_database(),
        'cache': check_cache(),
        'email': check_email_backend(),
    }
    
    # Overall health
    all_healthy = all(is_healthy for is_healthy, _ in checks.values())
    
    status_code = 200 if all_healthy else 503
    
    response_data = {
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': {
            name: {
                'healthy': is_healthy,
                'message': message,
            }
            for name, (is_healthy, message) in checks.items()
        },
    }
    
    return JsonResponse(response_data, status=status_code)




