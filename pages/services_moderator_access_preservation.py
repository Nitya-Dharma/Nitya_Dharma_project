"""
Service functions for preserving moderator access when granting Admin Pandit is removed.

TASK 12: Moderator Access Granted by Removed Admin Pandit

This module ensures that:
- Moderator role remains active
- Grantor preserved in audit history
- Super Admin becomes role custodian (not grantor)
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from pages.models_role_assignment import PageRoleAssignment

User = get_user_model()
logger = logging.getLogger(__name__)


def preserve_moderator_access_on_grantor_deactivation(admin_pandit, actor=None):
    """
    TASK 12: Preserve moderator access when granting Admin Pandit is removed.
    
    This function:
    - Ensures moderator roles remain active
    - Preserves grantor in audit history
    - Super Admin becomes role custodian (logically, not via FK)
    
    Args:
        admin_pandit: User instance (must have role='admin')
        actor: User instance (Super Admin performing deactivation)
    
    Returns:
        dict: Summary of preserved moderator access
    
    Raises:
        ValidationError: If user is not an Admin Pandit
    """
    if admin_pandit.role != 'admin':
        raise ValidationError(f"User {admin_pandit.email} is not an Admin Pandit.")
    
    with transaction.atomic():
        # Find all active role assignments granted by this Admin Pandit
        assignments = PageRoleAssignment.objects.filter(
            granted_by=admin_pandit,
            revoked_at__isnull=True  # Only active assignments
        )
        assignment_count = assignments.count()
        
        if assignment_count == 0:
            logger.info(f"Admin Pandit {admin_pandit.email} granted no active moderator roles")
            return {
                'assignment_count': 0,
                'assignments_preserved': [],
                'message': 'No active moderator roles to preserve'
            }
        
        # granted_by is preserved (SET_NULL on delete, but we're deactivating, not deleting)
        # When Admin Pandit is deactivated, granted_by remains but is inactive
        # Moderator roles remain active
        # Super Admin becomes custodian logically (not via FK overwrite)
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            admin_pandit,
            actor=actor,
            reason=f"GRANTOR_DEACTIVATED - {assignment_count} moderator role(s) preserved, Super Admin is now custodian"
        )
        
        logger.info(
            f"Moderator access preserved after grantor deactivation - "
            f"Admin: {admin_pandit.email}, Active roles: {assignment_count}"
        )
        
        return {
            'assignment_count': assignment_count,
            'assignments_preserved': [a.id for a in assignments],
            'message': f'{assignment_count} moderator role(s) preserved - Super Admin is now custodian'
        }







