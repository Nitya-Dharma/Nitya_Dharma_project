"""
Service functions for rerouting page access requests when Admin Pandit is removed.

TASK 13: Pandit Access Requests When Admin Pandit Is Removed

This module ensures that:
- Requests are never lost
- Requests are rerouted to Super Admin when Admin Pandit is removed
- Original request metadata is preserved
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from pages.models_access_request import PageAccessRequest

User = get_user_model()
logger = logging.getLogger(__name__)


def reroute_access_requests_on_admin_deactivation(admin_pandit, actor=None):
    """
    TASK 13: Reroute pending access requests when Admin Pandit is removed.
    
    This function:
    - Finds all pending requests assigned to Admin Pandit
    - Sets requested_to to NULL (reassigned to Super Admin logically)
    - Preserves original request metadata
    - Logs audit events
    
    Args:
        admin_pandit: User instance (must have role='admin')
        actor: User instance (Super Admin performing deactivation)
    
    Returns:
        dict: Summary of rerouted requests
    
    Raises:
        ValidationError: If user is not an Admin Pandit
    """
    if admin_pandit.role != 'admin':
        raise ValidationError(f"User {admin_pandit.email} is not an Admin Pandit.")
    
    with transaction.atomic():
        # Find all pending requests assigned to this Admin Pandit
        requests = PageAccessRequest.objects.filter(
            requested_to=admin_pandit,
            status=PageAccessRequest.STATUS_PENDING
        )
        request_count = requests.count()
        
        if request_count == 0:
            logger.info(f"Admin Pandit {admin_pandit.email} has no pending access requests")
            return {
                'request_count': 0,
                'requests_rerouted': [],
                'message': 'No pending requests to reroute'
            }
        
        # Reassign to Super Admin (set requested_to to NULL)
        # Super Admin becomes reviewer logically (not via FK overwrite)
        rerouted_ids = []
        for request in requests:
            request.requested_to = None  # NULL means Super Admin is now reviewer
            request.save(update_fields=['requested_to'])
            rerouted_ids.append(request.id)
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            admin_pandit,
            actor=actor,
            reason=f"REQUEST_REASSIGNED_TO_SUPER_ADMIN - {request_count} pending request(s) rerouted"
        )
        
        logger.info(
            f"Access requests rerouted to Super Admin - "
            f"Admin: {admin_pandit.email}, Requests rerouted: {request_count}"
        )
        
        return {
            'request_count': request_count,
            'requests_rerouted': rerouted_ids,
            'message': f'{request_count} pending request(s) rerouted to Super Admin'
        }


def get_pending_requests_for_super_admin():
    """
    Get all pending access requests that should be reviewed by Super Admin.
    
    This includes:
    - Requests where requested_to is NULL (reassigned)
    - Requests where requested_to is inactive
    
    Returns:
        QuerySet: Pending access requests for Super Admin
    """
    # Requests with NULL requested_to (reassigned to Super Admin)
    null_requests = PageAccessRequest.objects.filter(
        requested_to__isnull=True,
        status=PageAccessRequest.STATUS_PENDING
    )
    
    # Requests where requested_to is inactive
    inactive_requests = PageAccessRequest.objects.filter(
        requested_to__isnull=False,
        requested_to__is_active=False,
        status=PageAccessRequest.STATUS_PENDING
    )
    
    # Combine and return
    return (null_requests | inactive_requests).distinct().order_by('-created_at')







