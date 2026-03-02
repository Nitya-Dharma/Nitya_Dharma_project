"""
Service functions for handling Admin Pandit approval history preservation.

TASK 2: Admin Pandit Approval History Preservation

This module handles:
- Preserving approval records when Admin Pandit is deactivated
- Assigning approval custodianship to Super Admin
- Ensuring approval history remains immutable
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)

try:
    from governance.approvals.models import ApprovalRecord, ApprovalCustodian
except ImportError:
    ApprovalRecord = None
    ApprovalCustodian = None


def handle_admin_deactivation(admin_pandit, actor=None):
    """
    Handle Admin Pandit deactivation while preserving approval history.
    
    TASK 2: Ensures that:
    - Approval records remain unchanged
    - Approved Pandits remain approved
    - Approval authority history is preserved
    - Super Admin becomes approval custodian
    
    Args:
        admin_pandit: User instance (must have role='admin')
        actor: User instance (Super Admin performing deactivation)
    
    Returns:
        dict: Summary of actions taken
    
    Raises:
        ValidationError: If admin_pandit is not an admin
    """
    if admin_pandit.role != 'admin':
        raise ValidationError(f"User {admin_pandit.email} is not an Admin Pandit.")
    
    if not ApprovalRecord:
        logger.warning("ApprovalRecord model not available - skipping approval custodianship")
        return {}
    
    with transaction.atomic():
        # Find all approval records where this Admin Pandit approved others
        approval_records = ApprovalRecord.objects.filter(
            approved_by_admin=admin_pandit
        )
        
        approval_count = approval_records.count()
        
        if approval_count == 0:
            logger.info(f"Admin {admin_pandit.email} has no approval records - no custodianship needed")
            return {
                'approval_count': 0,
                'custodianship_assigned': False
            }
        
        # Find Super Admin to assign as custodian
        super_admin = User.objects.filter(is_superuser=True, is_active=True).first()
        if not super_admin:
            logger.error("No active Super Admin found to assign approval custodianship!")
            raise ValidationError("No active Super Admin available for approval custodianship.")
        
        # Ensure display names are captured for all approval records
        for record in approval_records:
            if not record.approved_by_display_name:
                record.approved_by_display_name = _get_admin_display_name(admin_pandit)
                record.save(update_fields=['approved_by_display_name'])
        
        # Assign approval custodian for this Admin Pandit
        custodian, created = ApprovalCustodian.objects.get_or_create(
            original_admin_pandit=admin_pandit,
            defaults={
                'custodian': super_admin,
                'reason': f"Admin Pandit {admin_pandit.email} deactivated. Approval history preserved."
            }
        )
        
        # Update all approval records to reference custodian
        approval_records.update(approval_custodian=super_admin)
        
        # Log audit event
        from core.audit import log_custodianship_assignment
        log_custodianship_assignment(
            original_referrer=admin_pandit,  # Reusing function signature
            custodian=super_admin,
            reason=f"Approval custodianship assigned for {approval_count} approval record(s)",
            actor=actor
        )
        
        logger.info(
            f"Approval custodianship assigned - "
            f"Admin: {admin_pandit.email}, Custodian: {super_admin.email}, "
            f"Approval records: {approval_count}"
        )
        
        return {
            'approval_count': approval_count,
            'custodianship_assigned': True,
            'custodian': super_admin.email
        }


def _get_admin_display_name(admin_user):
    """Get display name for Admin Pandit."""
    if admin_user.username:
        return admin_user.username
    elif admin_user.get_full_name():
        return admin_user.get_full_name()
    else:
        return admin_user.email


def create_approval_record(pandit, approved_by_admin=None, actor=None):
    """
    Create an approval record when a Pandit is approved.
    
    Args:
        pandit: User instance (must have role='pandit')
        approved_by_admin: User instance (Admin Pandit who approved, optional)
        actor: User instance (for audit logging)
    
    Returns:
        ApprovalRecord: Created approval record
    """
    if not ApprovalRecord:
        logger.warning("ApprovalRecord model not available - cannot create approval record")
        return None
    
    if pandit.role != 'pandit':
        raise ValidationError(f"User {pandit.email} is not a Pandit.")
    
    # Get display name for Admin Pandit
    display_name = None
    if approved_by_admin:
        display_name = _get_admin_display_name(approved_by_admin)
    else:
        # Super Admin approved
        display_name = "Super Admin"
    
    # Create or update approval record
    approval_record, created = ApprovalRecord.objects.update_or_create(
        approved_pandit=pandit,
        defaults={
            'approved_by_admin': approved_by_admin,
            'approved_by_display_name': display_name,
            'created_at': timezone.now()
        }
    )
    
    logger.info(
        f"Approval record {'created' if created else 'updated'} - "
        f"Pandit: {pandit.email}, Approved by: {display_name}"
    )
    
    return approval_record
