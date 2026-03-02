"""
Service functions for handling Temple Page deactivation.

TASK 6: Temple Page Deactivation (No Hard Delete)

This module ensures that:
- Pages are never hard-deleted
- URLs continue to resolve
- Content remains stored
- Reviews, posts, engagement remain intact
- Only Super Admin can reactivate
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from pages.models import Page
from pages.constants import PAGE_STATUS_INVISIBLE, PAGE_STATUS_DEACTIVATED, PAGE_STATUS_ACTIVE

User = get_user_model()
logger = logging.getLogger(__name__)


def deactivate_page(page, reason=None, status=None, actor=None):
    """
    TASK 6: Deactivate a Temple Page without data loss.
    
    This function:
    - Sets page status to INVISIBLE or DEACTIVATED
    - Preserves all content (posts, reviews, engagement)
    - URL continues to resolve
    - Only Super Admin can perform this action
    
    Args:
        page: Page instance to deactivate
        reason (str, optional): Reason for deactivation
        status (str, optional): Target status ('INVISIBLE' or 'DEACTIVATED'). Defaults to 'INVISIBLE'
        actor (User, optional): User performing deactivation (must be Super Admin)
    
    Returns:
        dict: Summary of deactivation
    
    Raises:
        ValidationError: If actor is not Super Admin or page is already deactivated
    """
    if actor and not actor.is_superuser:
        raise ValidationError("Only Super Admin can deactivate pages.")
    
    if status is None:
        status = PAGE_STATUS_INVISIBLE
    
    if status not in [PAGE_STATUS_INVISIBLE, PAGE_STATUS_DEACTIVATED]:
        raise ValidationError(f"Invalid deactivation status: {status}. Must be INVISIBLE or DEACTIVATED.")
    
    if page.status == status:
        raise ValidationError(f"Page {page.title} is already {status}.")
    
    with transaction.atomic():
        # Deactivate the page
        page.deactivate(
            reason=reason or "Page deactivated by Super Admin",
            status=status,
            actor=actor
        )
        
        logger.info(
            f"Page deactivated - "
            f"Page: {page.title} (ID: {page.id}), Status: {status}, "
            f"Reason: {reason or 'N/A'}, Actor: {actor.email if actor else 'System'}"
        )
        
        # TASK 26: Log audit event for page deactivation
        try:
            from core.models_audit_log import create_audit_log
            create_audit_log(
                action_type='DEACTIVATE',
                actor=actor,
                target_entity_type='Page',
                target_entity_id=page.id,
                target_entity_public_id=page.public_id,
                metadata={'status': status, 'reason': reason or 'N/A'}
            )
        except Exception as e:
            logger.warning(f"TASK 26: Failed to create audit log for page deactivation: {e}")
        
        # TASK 26: Log that engagement history is preserved
        try:
            from core.audit import log_deactivation
            log_deactivation(
                page,
                actor=actor,
                reason="PAGE_MARKED_INVISIBLE - Engagement history preserved"
            )
        except Exception:
            pass
        
        # TASK 29: Preserve followers when page is deactivated
        try:
            from .services_follower_preservation import preserve_followers_on_page_deactivation
            preserve_followers_on_page_deactivation(page, actor=actor)
        except Exception as e:
            logger.warning(f"TASK 29: Error preserving followers: {e}")
        
        return {
            'page_id': page.id,
            'page_title': page.title,
            'status': page.status,
            'deactivated_at': page.deactivated_at,
            'reason': page.visibility_reason
        }


def reactivate_page(page, reason=None, actor=None):
    """
    TASK 6: Reactivate a Temple Page.
    
    Only Super Admin can reactivate pages.
    
    Args:
        page: Page instance to reactivate
        reason (str, optional): Reason for reactivation
        actor (User, optional): User performing reactivation (must be Super Admin)
    
    Returns:
        dict: Summary of reactivation
    
    Raises:
        ValidationError: If actor is not Super Admin or page is already active
    """
    if actor and not actor.is_superuser:
        raise ValidationError("Only Super Admin can reactivate pages.")
    
    if page.status == PAGE_STATUS_ACTIVE:
        raise ValidationError(f"Page {page.title} is already active.")
    
    with transaction.atomic():
        # Reactivate the page
        page.reactivate(
            reason=reason or "Page reactivated by Super Admin",
            actor=actor
        )
        
        logger.info(
            f"Page reactivated - "
            f"Page: {page.title} (ID: {page.id}), "
            f"Reason: {reason or 'N/A'}, Actor: {actor.email if actor else 'System'}"
        )
        
        # TASK 29: Restore followers when page is reactivated
        try:
            from .services_follower_preservation import restore_followers_on_page_reactivation
            restore_followers_on_page_reactivation(page, actor=actor)
        except Exception as e:
            logger.warning(f"TASK 29: Error restoring followers: {e}")
        
        return {
            'page_id': page.id,
            'page_title': page.title,
            'status': page.status,
            'reactivated_at': page.reactivated_at,
            'reason': reason or 'N/A'
        }

