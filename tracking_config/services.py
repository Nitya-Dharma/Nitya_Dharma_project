"""
Service functions for tracking configuration.

These functions handle tracking configuration retrieval and route exclusion logic.
All functions fail silently and never raise errors to templates.
"""
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger(__name__)


def get_active_tracking_configuration():
    """
    Get the active tracking configuration.
    
    Returns:
        TrackingConfiguration instance or None
    """
    try:
        from .models import TrackingConfiguration
        return TrackingConfiguration.objects.filter(is_active=True).first()
    except Exception as e:
        logger.warning(f"Error fetching active tracking configuration: {str(e)}")
        return None


def is_route_excluded(path, config):
    """
    Check if a route should be excluded from tracking.
    
    Args:
        path: Request path (e.g., '/dashboard/admin/')
        config: TrackingConfiguration instance
    
    Returns:
        True if route should be excluded, False otherwise
    """
    if not config:
        return True
    
    # Always exclude dashboards and admin routes
    excluded_patterns = [
        '/dashboard/',
        '/admin/',
        '/accounts/settings/',
        '/accounts/logout/',
    ]
    
    # Check hardcoded exclusions
    for pattern in excluded_patterns:
        if pattern in path:
            return True
    
    # Check user-defined exclusions
    user_excluded = config.get_excluded_patterns_list()
    for pattern in user_excluded:
        if pattern in path:
            return True
    
    return False


def get_tracking_payload(request):
    """
    Get tracking payload for template context.
    
    Args:
        request: Django request object
    
    Returns:
        dict with 'tracking' key containing head, body, footer snippets
        or None if tracking should not be injected
    """
    try:
        config = get_active_tracking_configuration()
        
        if not config:
            return None
        
        # Check if route is excluded
        if is_route_excluded(request.path, config):
            return None
        
        # Build payload
        payload = {
            'tracking': {
                'head': config.head_snippet or '',
                'body': config.body_snippet or '',
                'footer': config.footer_snippet or '',
            }
        }
        
        return payload
        
    except Exception as e:
        logger.warning(f"Error getting tracking payload: {str(e)}")
        return None


