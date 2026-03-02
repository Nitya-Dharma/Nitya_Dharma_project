"""
Service functions for handling Pandit page role assignment deactivation.

TASK 3: Pandit Associated with Multiple Temple Pages

This module handles:
- Revoking page role assignments when Pandit is deactivated
- Preserving association history
- Assigning page custodianship to Super Admin
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)

try:
    from pages.models_role_assignment import PageRoleAssignment, PageCustodian
except ImportError:
    PageRoleAssignment = None
    PageCustodian = None


def handle_pandit_page_deactivation(pandit, actor=None):
    """
    Handle Pandit deactivation when Pandit has page role assignments.
    
    TASK 3: Ensures that:
    - Pandit loses all edit/moderation permissions
    - Pages remain ACTIVE and visible
    - Association history preserved
    - Super Admin becomes temporary page custodian
    
    Args:
        pandit: User instance (must have role='pandit')
        actor: User instance (Super Admin performing deactivation)
    
    Returns:
        dict: Summary of actions taken
    
    Raises:
        ValidationError: If pandit is not a Pandit
    """
    if pandit.role != 'pandit':
        raise ValidationError(f"User {pandit.email} is not a Pandit.")
    
    if not PageRoleAssignment:
        logger.warning("PageRoleAssignment model not available - skipping page role custodianship")
        return {}
    
    with transaction.atomic():
        # Find all active page role assignments for this Pandit
        active_assignments = PageRoleAssignment.objects.filter(
            pandit=pandit,
            revoked_at__isnull=True
        )
        
        assignment_count = active_assignments.count()
        
        if assignment_count == 0:
            logger.info(f"Pandit {pandit.email} has no active page role assignments")
            raise ValidationError("Pandit has no active page role assignments")
        
        # Find Super Admin to assign as custodian
        super_admin = User.objects.filter(is_superuser=True, is_active=True).first()
        if not super_admin:
            logger.error("No active Super Admin found to assign page custodianship!")
            raise ValidationError("No active Super Admin available for page custodianship.")
        
        # Revoke all role assignments
        revoked_pages = []
        for assignment in active_assignments:
            assignment.revoke(
                reason=f"Pandit {pandit.email} deactivated - role revoked",
                actor=actor
            )
            revoked_pages.append(assignment.page)
        
        # Assign page custodianship for each affected page
        custodianships_created = 0
        for page in revoked_pages:
            # Check if custodianship already exists
            existing = PageCustodian.objects.filter(
                page=page,
                original_pandit=pandit
            ).exists()
            
            if not existing:
                PageCustodian.objects.create(
                    page=page,
                    original_pandit=pandit,
                    custodian=super_admin,
                    reason=f"Pandit {pandit.email} deactivated - page role revoked"
                )
                custodianships_created += 1
        
        # Log audit events
        from core.audit import log_deactivation
        log_deactivation(
            pandit,
            actor=actor,
            reason=f"Page role assignments revoked for {assignment_count} page(s)"
        )
        
        logger.info(
            f"Page role custodianship assigned - "
            f"Pandit: {pandit.email}, Custodian: {super_admin.email}, "
            f"Pages affected: {assignment_count}, Custodianships created: {custodianships_created}"
        )
        
        return {
            'assignment_count': assignment_count,
            'pages_affected': [p.id for p in revoked_pages],
            'custodianships_created': custodianships_created,
            'custodian': super_admin.email
        }


def revoke_page_role(assignment, reason=None, actor=None):
    """
    TASK 5: Manually revoke a page role assignment.
    
    This function handles moderator/admin role removal while preserving:
    - All historical edits and posts
    - Content attribution
    - Audit history
    
    Args:
        assignment: PageRoleAssignment instance to revoke
        reason (str, optional): Reason for revocation
        actor (User, optional): User performing revocation (must be Super Admin)
    
    Returns:
        dict: Summary of revocation
    
    Raises:
        ValidationError: If assignment is already revoked or actor is not authorized
    """
    if not PageRoleAssignment:
        raise ValidationError("PageRoleAssignment model not available")
    
    if assignment.revoked_at:
        raise ValidationError(f"Role assignment for {assignment.pandit.email} on {assignment.page.title} is already revoked.")
    
    # Verify actor is Super Admin
    if actor and not actor.is_superuser:
        raise ValidationError("Only Super Admin can revoke page roles.")
    
    with transaction.atomic():
        # Revoke the role assignment
        assignment.revoke(
            reason=reason or "Role revoked by Super Admin",
            actor=actor
        )
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            assignment,
            actor=actor,
            reason=f"PAGE_ROLE_REVOKED - {assignment.role} role removed from {assignment.pandit.email} on {assignment.page.title}"
        )
        
        logger.info(
            f"Page role revoked - "
            f"Pandit: {assignment.pandit.email}, Page: {assignment.page.title}, "
            f"Role: {assignment.role}, Reason: {reason or 'N/A'}"
        )
        
        return {
            'assignment_id': assignment.id,
            'pandit': assignment.pandit.email,
            'page': assignment.page.title,
            'role': assignment.role,
            'revoked_at': assignment.revoked_at,
            'reason': assignment.revoked_reason
        }
