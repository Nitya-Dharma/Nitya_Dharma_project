"""
Context processor for tracking configuration.

Injects tracking snippets into template context for public pages only.
Completely invisible to Admin Pandit, Pandit, and End Users.
"""
from .services import get_tracking_payload


def tracking_context(request):
    """
    Context processor that provides tracking snippets to templates.
    
    Returns:
        dict with 'tracking' key containing head, body, footer snippets
        or empty dict if tracking should not be injected
    """
    payload = get_tracking_payload(request)
    
    if payload:
        return payload
    
    # Return empty dict if no tracking
    return {'tracking': None}


