"""
Service functions for enforcing slug immutability.

TASK 30: Page Slug Immutability After Followers

This module ensures that:
- Slug becomes locked once followers > 0
- Page cannot be deleted if it has followers
- URL always resolves by slug
- Slug cannot be reused
"""

import logging
from django.core.exceptions import ValidationError
from .models import Page

logger = logging.getLogger(__name__)


def can_change_slug(page: Page) -> tuple[bool, str]:
    """
    TASK 30: Check if page slug can be changed.
    
    Args:
        page: Page instance
    
    Returns:
        tuple: (can_change: bool, reason: str)
    """
    if page.followers_count > 0:
        return (
            False,
            f"Slug cannot be changed after the page has followers. "
            f"Current followers: {page.followers_count}. "
            f"Slug '{page.slug}' is locked to preserve shared URLs and bookmarks."
        )
    
    return (True, "Slug can be changed (no followers)")


def validate_slug_change(page: Page, new_slug: str):
    """
    TASK 30: Validate slug change attempt.
    
    Args:
        page: Page instance
        new_slug: Proposed new slug
    
    Raises:
        ValidationError: If slug change is not allowed
    """
    if page.followers_count > 0 and page.slug != new_slug:
        from core.audit import log_blocked_deletion
        log_blocked_deletion(
            page,
            actor=None,
            reason=f"SLUG_LOCKED - Slug change blocked, page has {page.followers_count} follower(s)"
        )
        raise ValidationError(
            f"Slug cannot be changed after the page has followers. "
            f"Current followers: {page.followers_count}. "
            f"Slug '{page.slug}' is locked to preserve shared URLs and bookmarks."
        )


def can_delete_page(page: Page) -> tuple[bool, str]:
    """
    TASK 30: Check if page can be deleted.
    
    Args:
        page: Page instance
    
    Returns:
        tuple: (can_delete: bool, reason: str)
    """
    if page.followers_count > 0:
        return (
            False,
            f"Page cannot be deleted because it has {page.followers_count} follower(s). "
            f"Use deactivate() to set status='INVISIBLE' instead. "
            f"Slug and URL will remain accessible."
        )
    
    # Even without followers, hard delete is not allowed
    return (
        False,
        "Hard deletion is not allowed for Pages. Use deactivate() to set status='INVISIBLE' instead."
    )


def resolve_page_by_slug(page_type: str, slug: str, include_invisible: bool = True):
    """
    TASK 30: Resolve page by slug, including invisible pages.
    
    This ensures that URLs always resolve, even if page is INVISIBLE.
    
    Args:
        page_type: Type of page
        slug: Page slug
        include_invisible: If True, return page even if INVISIBLE
    
    Returns:
        Page instance or None
    """
    try:
        if include_invisible:
            # TASK 30: Always resolve by slug, even if INVISIBLE
            page = Page.objects.get(page_type=page_type, slug=slug, is_deleted=False)
            return page
        else:
            # Only return ACTIVE pages
            from .constants import PAGE_STATUS_ACTIVE
            page = Page.objects.get(
                page_type=page_type,
                slug=slug,
                status=PAGE_STATUS_ACTIVE,
                is_deleted=False
            )
            return page
    except Page.DoesNotExist:
        return None


def get_page_display_for_url(page: Page) -> dict:
    """
    TASK 30: Get display information for page URL resolution.
    
    If page is invisible, returns appropriate message.
    
    Args:
        page: Page instance
    
    Returns:
        dict: Display information
    """
    from .constants import PAGE_STATUS_INVISIBLE, PAGE_STATUS_DEACTIVATED
    
    if page.status in [PAGE_STATUS_INVISIBLE, PAGE_STATUS_DEACTIVATED]:
        return {
            'is_visible': False,
            'message': 'This page is currently unavailable.',
            'status': page.status,
            'title': page.title,  # Still show title for context
            'slug': page.slug,  # Slug preserved
            'public_id': page.public_id  # Public ID preserved
        }
    
    return {
        'is_visible': True,
        'title': page.title,
        'slug': page.slug,
        'public_id': page.public_id,
        'status': page.status
    }







