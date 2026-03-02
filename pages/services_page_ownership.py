"""
Service functions for handling Temple Page ownership preservation.

TASK 4: Temple Page Created by Admin Pandit

This module handles:
- Preserving page creator identity when Admin Pandit is deactivated
- Assigning page custodianship to Super Admin
- Ensuring pages remain accessible
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)

try:
    from pages.models import Page
    from pages.models_role_assignment import PageCustodian
except ImportError:
    Page = None
    PageCustodian = None


def handle_page_creator_deactivation(admin_pandit, actor=None):
    """
    Handle Admin Pandit deactivation when Admin Pandit created Temple Pages.
    
    TASK 4: Ensures that:
    - Temple Pages remain ACTIVE or INVISIBLE (never deleted)
    - Creator remains recorded as original creator
    - Super Admin becomes page custodian
    - Page actions continue under Super Admin authority
    
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
    
    if not Page:
        logger.warning("Page model not available - skipping page ownership custodianship")
        return {}
    
    with transaction.atomic():
        # Find all pages created by this Admin Pandit
        created_pages = Page.objects.filter(created_by=admin_pandit)
        
        page_count = created_pages.count()
        
        if page_count == 0:
            logger.info(f"Admin {admin_pandit.email} created no pages - no custodianship needed")
            raise ValidationError("Admin created no pages")
        
        # Find Super Admin to assign as custodian
        super_admin = User.objects.filter(is_superuser=True, is_active=True).first()
        if not super_admin:
            logger.error("No active Super Admin found to assign page custodianship!")
            raise ValidationError("No active Super Admin available for page custodianship.")
        
        # Ensure display names are captured for all pages
        display_name = _get_admin_display_name(admin_pandit)
        for page in created_pages:
            if not page.created_by_display_name:
                page.created_by_display_name = display_name
                page.save(update_fields=['created_by_display_name'])
        
        # Assign page custodian for each page
        custodianships_created = 0
        for page in created_pages:
            # Check if custodianship already exists
            existing = PageCustodian.objects.filter(
                page=page,
                original_pandit=admin_pandit
            ).exists()
            
            if not existing:
                PageCustodian.objects.create(
                    page=page,
                    original_pandit=admin_pandit,
                    custodian=super_admin,
                    reason=f"Admin Pandit {admin_pandit.email} deactivated - page ownership custodianship"
                )
                custodianships_created += 1
            
            # Update page custodian field
            if not page.custodian:
                page.custodian = super_admin
                page.save(update_fields=['custodian'])
        
        # Log audit event
        from core.audit import log_custodianship_assignment
        log_custodianship_assignment(
            original_referrer=admin_pandit,  # Reusing function signature
            custodian=super_admin,
            reason=f"Page ownership custodianship assigned for {page_count} page(s)",
            actor=actor
        )
        
        logger.info(
            f"Page ownership custodianship assigned - "
            f"Admin: {admin_pandit.email}, Custodian: {super_admin.email}, "
            f"Pages: {page_count}, Custodianships created: {custodianships_created}"
        )
        
        return {
            'page_count': page_count,
            'custodianships_created': custodianships_created,
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
