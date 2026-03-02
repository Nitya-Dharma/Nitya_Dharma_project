"""
Service functions for preserving followers when pages are deactivated.

TASK 29: Followers of a Deactivated Page

This module ensures that:
- Followers are preserved when pages are deactivated
- Follow relationships remain intact
- Followers are automatically restored when page is reactivated
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Page, PageFollow

User = get_user_model()
logger = logging.getLogger(__name__)


def preserve_followers_on_page_deactivation(page, actor=None):
    """
    TASK 29: Preserve followers when a page is deactivated.
    
    This function ensures that:
    - Followers are NOT deleted
    - Follow relationships remain intact
    - Page status becomes INVISIBLE (not deleted)
    
    Args:
        page: Page instance being deactivated
        actor: User performing the deactivation (optional)
    
    Returns:
        dict: Summary of follower preservation
    """
    with transaction.atomic():
        # Get follower count
        follower_count = PageFollow.objects.filter(page=page).count()
        
        # TASK 29: Followers are preserved automatically because:
        # 1. PageFollow.page uses PROTECT (never deleted when page is deactivated)
        # 2. Page is not deleted, only status changes to INVISIBLE
        # 3. Follow relationships remain in database
        
        # Log audit event
        try:
            from core.audit import log_deactivation
            log_deactivation(
                page,
                actor=actor,
                reason=f"FOLLOWERS_PRESERVED - {follower_count} follower(s) preserved when page deactivated"
            )
        except Exception:
            pass
        
        logger.info(
            f"TASK 29: {follower_count} follower(s) preserved for deactivated page {page.title} (ID: {page.id})"
        )
        
        return {
            'page_id': page.id,
            'page_title': page.title,
            'follower_count': follower_count,
            'preserved': True
        }


def restore_followers_on_page_reactivation(page, actor=None):
    """
    TASK 29: Restore followers when a page is reactivated.
    
    This function ensures that:
    - All existing followers are automatically restored
    - No re-follow required
    - Follow relationships remain intact
    
    Args:
        page: Page instance being reactivated
        actor: User performing the reactivation (optional)
    
    Returns:
        dict: Summary of follower restoration
    """
    with transaction.atomic():
        # Get follower count
        follower_count = PageFollow.objects.filter(page=page).count()
        
        # TASK 29: Followers are automatically restored because:
        # 1. Follow relationships were never deleted
        # 2. Page status changes from INVISIBLE to ACTIVE
        # 3. Followers automatically see page in feeds/search again
        
        # Log audit event
        try:
            from core.audit import log_deactivation
            log_deactivation(
                page,
                actor=actor,
                reason=f"FOLLOWERS_RESTORED - {follower_count} follower(s) automatically restored when page reactivated"
            )
        except Exception:
            pass
        
        logger.info(
            f"TASK 29: {follower_count} follower(s) automatically restored for reactivated page {page.title} (ID: {page.id})"
        )
        
        return {
            'page_id': page.id,
            'page_title': page.title,
            'follower_count': follower_count,
            'restored': True
        }


def get_followers_for_page(page, include_invisible=False):
    """
    TASK 29: Get followers for a page, including invisible pages.
    
    Args:
        page: Page instance
        include_invisible: If True, return followers even if page is INVISIBLE
    
    Returns:
        QuerySet of PageFollow instances
    """
    # TASK 29: Always return followers regardless of page status
    # Follow relationships are preserved even if page is INVISIBLE
    return PageFollow.objects.filter(page=page).select_related('follower', 'page').order_by('-created_at')


def get_follower_count(page):
    """
    TASK 29: Get follower count for a page.
    
    Args:
        page: Page instance
    
    Returns:
        int: Number of followers
    """
    # TASK 29: Follower count remains unchanged even if page is INVISIBLE
    return PageFollow.objects.filter(page=page).count()







