"""
Page selectors for access control and listing.

STRICT RULES:
- NO views, NO UI handling
- Backend-only data retrieval
- Role-based access control
- Returns data structures, not HTTP responses
"""

import logging
from typing import Dict, Any, Optional, List
from django.contrib.auth import get_user_model
from core.public_id import resolve_public_id, reject_bigint_id
from .models import Page
from .constants import (
    PAGE_STATUS_ACTIVE,
    PAGE_STATUS_DEACTIVATED,
    PAGE_STATUS_INVISIBLE,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def _is_super_admin(user):
    """Check if user is Super Admin."""
    return user and user.is_authenticated and user.is_superuser


def _is_admin_pandit(user):
    """Check if user is Admin Pandit."""
    return user and user.is_authenticated and user.role == 'admin' and not user.is_superuser


def _can_view_invisible_page(user, page):
    """
    Check if user can view an INVISIBLE page.
    
    Rules:
    - SUPER_ADMIN: Can view any INVISIBLE page
    - ADMIN_PANDIT: Can view INVISIBLE pages they created
    - Others: Cannot view INVISIBLE pages
    
    Args:
        user: User instance (can be None for anonymous)
        page: Page instance
    
    Returns:
        bool: True if user can view this INVISIBLE page
    """
    if not page or page.status != PAGE_STATUS_INVISIBLE:
        return False  # Not applicable for non-INVISIBLE pages
    
    if _is_super_admin(user):
        return True  # Super Admin can view any INVISIBLE page
    
    if _is_admin_pandit(user) and page.created_by == user:
        return True  # Admin Pandit can view their own INVISIBLE pages
    
    return False  # Others cannot view INVISIBLE pages


def get_page_by_public_id(user, page_public_id) -> Optional[Dict[str, Any]]:
    """
    Get page by public_id with access control rules.
    
    Rules:
    - ACTIVE: Visible to all
    - DEACTIVATED: Visible to all with status flag
    - INVISIBLE: Visible ONLY if:
        - user is SUPER_ADMIN
        - OR user is creator (ADMIN_PANDIT)
      Others see None (404-like response)
    
    Args:
        user: User instance (can be None for anonymous users)
        page_public_id: Public ID (UUIDv7) of the page
    
    Returns:
        Dict with:
            - 'page': Page object (if accessible)
            - 'is_visible': bool (whether page is visible to user)
            - 'status': str (page status)
            - 'show_banner': bool (whether to show status banner)
            - 'banner_message': str (banner message if applicable)
        None if page not found or not accessible
    
    Note: Does NOT raise 404. Returns None for not found/not accessible.
    """
    if reject_bigint_id(page_public_id):
        logger.warning(f"Invalid page_public_id format: {page_public_id}")
        return None
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        logger.debug(f"Page not found: {page_public_id}")
        return None
    
    # Build response metadata
    result = {
        'page': page,
        'status': page.status,
        'is_visible': False,
        'show_banner': False,
        'banner_message': None,
    }
    
    # ACTIVE: Visible to all
    if page.status == PAGE_STATUS_ACTIVE:
        result['is_visible'] = True
        result['show_banner'] = False
        result['banner_message'] = None
        return result
    
    # DEACTIVATED: Visible to all with status flag
    if page.status == PAGE_STATUS_DEACTIVATED:
        result['is_visible'] = True
        result['show_banner'] = True
        result['banner_message'] = "This page is deactivated"
        return result
    
    # INVISIBLE: Visible only to SUPER_ADMIN or creator (ADMIN_PANDIT)
    if page.status == PAGE_STATUS_INVISIBLE:
        if _can_view_invisible_page(user, page):
            result['is_visible'] = True
            result['show_banner'] = True
            result['banner_message'] = "This page is invisible"
            return result
        else:
            # Not accessible - return None (404-like)
            logger.debug(f"Page {page_public_id} is INVISIBLE and user {user.email if user else 'anonymous'} cannot access it")
            return None
    
    # Unknown status - treat as not accessible
    logger.warning(f"Page {page_public_id} has unknown status: {page.status}")
    return None


def list_pages_for_admin_pandit(user) -> List[Page]:
    """
    List pages for Admin Pandit dashboard.
    
    Rules:
    - Only pages created by that admin pandit
    - Include ACTIVE + DEACTIVATED
    - Exclude INVISIBLE
    
    Args:
        user: User instance (must be authenticated Admin Pandit)
    
    Returns:
        List[Page]: QuerySet of pages accessible to this Admin Pandit
    
    Note: Returns empty list if user is not Admin Pandit or not authenticated.
    """
    if not user or not user.is_authenticated:
        logger.debug("Anonymous user cannot list pages for Admin Pandit")
        return Page.objects.none()
    
    if not _is_admin_pandit(user):
        logger.debug(f"User {user.email} is not Admin Pandit, cannot list pages")
        return Page.objects.none()
    
    # Get pages created by this Admin Pandit
    # Include ACTIVE and DEACTIVATED, exclude INVISIBLE
    pages = Page.objects.filter(
        created_by=user,
        status__in=[PAGE_STATUS_ACTIVE, PAGE_STATUS_DEACTIVATED]
    ).order_by('-created_at')
    
    logger.debug(f"Found {pages.count()} pages for Admin Pandit {user.email}")
    return pages


def list_pages_for_super_admin(user) -> List[Page]:
    """
    List pages for Super Admin dashboard.
    
    Rules:
    - All pages
    - All statuses (ACTIVE, DEACTIVATED, INVISIBLE)
    
    Args:
        user: User instance (must be authenticated Super Admin)
    
    Returns:
        List[Page]: QuerySet of all pages
    
    Note: Returns empty list if user is not Super Admin or not authenticated.
    """
    if not user or not user.is_authenticated:
        logger.debug("Anonymous user cannot list pages for Super Admin")
        return Page.objects.none()
    
    if not _is_super_admin(user):
        logger.debug(f"User {user.email} is not Super Admin, cannot list all pages")
        return Page.objects.none()
    
    # Get all pages, all statuses (select_related to avoid N+1 when rendering owner in dashboard)
    pages = Page.objects.select_related('created_by').all().order_by('-created_at')
    
    logger.debug(f"Found {pages.count()} pages for Super Admin {user.email}")
    return pages






















