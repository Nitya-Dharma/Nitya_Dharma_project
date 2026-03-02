"""
Dashboard data providers for page management.

STRICT RULES:
- READ ONLY data providers
- NO views, NO UI rendering
- NO analytics computation
- NO mutations or actions
- Returns data structures only
"""

import logging
from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model
from .models import Page
from .constants import (
    PAGE_TYPE_TEMPLE,
    PAGE_TYPE_BRAND,
    PAGE_TYPE_TRUST,
    PAGE_TYPE_SOCIAL_SERVICE,
    PAGE_STATUS_ACTIVE,
    PAGE_STATUS_DEACTIVATED,
    PAGE_STATUS_INVISIBLE,
)
from .selectors import _is_admin_pandit, _is_super_admin

User = get_user_model()
logger = logging.getLogger(__name__)


def get_admin_pandit_page_dashboard(user) -> Optional[Dict[str, Any]]:
    """
    Get dashboard data for Admin Pandit page management.
    
    Returns:
        Dict with:
            - total_pages_created: int
            - active_pages: int
            - deactivated_pages: int
            - referral_links_count: int (if referrals app exists)
            - last_created_page: Optional[Dict] (page data if exists)
        
        None if user is not Admin Pandit or not authenticated.
    
    Note: READ ONLY - no mutations, no actions.
    """
    if not user or not user.is_authenticated:
        logger.debug("Anonymous user cannot access Admin Pandit dashboard")
        return None
    
    if not _is_admin_pandit(user):
        logger.debug(f"User {user.email} is not Admin Pandit")
        return None
    
    # Get pages created by this Admin Pandit
    pages = Page.objects.filter(created_by=user)
    
    # Calculate counts
    total_pages_created = pages.count()
    active_pages = pages.filter(status=PAGE_STATUS_ACTIVE).count()
    deactivated_pages = pages.filter(status=PAGE_STATUS_DEACTIVATED).count()
    
    # Get referral links count (if referrals app exists)
    referral_links_count = 0
    try:
        from referrals.models import ReferralLink
        # Use the related_name 'created_referral_links' from ReferralLink model
        referral_links_count = user.created_referral_links.count()
    except ImportError:
        # Referrals app not available
        logger.debug("Referrals app not available, skipping referral_links_count")
    except AttributeError:
        # User model might not have the relation yet
        try:
            referral_links_count = ReferralLink.objects.filter(created_by=user).count()
        except Exception:
            referral_links_count = 0
    except Exception as e:
        logger.warning(f"Error fetching referral links count: {str(e)}")
        referral_links_count = 0
    
    # Get last created page (optional)
    last_created_page = None
    last_page = pages.order_by('-created_at').first()
    if last_page:
        last_created_page = {
            'public_id': last_page.public_id,
            'title': last_page.title,
            'page_type': last_page.page_type,
            'status': last_page.status,
            'created_at': last_page.created_at.isoformat() if last_page.created_at else None,
        }
    
    return {
        'total_pages_created': total_pages_created,
        'active_pages': active_pages,
        'deactivated_pages': deactivated_pages,
        'referral_links_count': referral_links_count,
        'last_created_page': last_created_page,
    }


def get_super_admin_page_overview() -> Dict[str, Any]:
    """
    Get system-level page overview for Super Admin dashboard.
    
    Returns:
        Dict with:
            - total_pages: int
            - pages_by_type: Dict[str, int] (count per page type)
            - pages_by_status: Dict[str, int] (count per status)
            - deactivated_pages_count: int
            - invisible_pages_count: int
    
    Note: READ ONLY - no mutations, no actions. System-level visibility only.
    """
    # Get all pages
    all_pages = Page.objects.all()
    
    # Total count
    total_pages = all_pages.count()
    
    # Count by type
    pages_by_type = {
        PAGE_TYPE_TEMPLE: all_pages.filter(page_type=PAGE_TYPE_TEMPLE).count(),
        PAGE_TYPE_BRAND: all_pages.filter(page_type=PAGE_TYPE_BRAND).count(),
        PAGE_TYPE_TRUST: all_pages.filter(page_type=PAGE_TYPE_TRUST).count(),
        PAGE_TYPE_SOCIAL_SERVICE: all_pages.filter(page_type=PAGE_TYPE_SOCIAL_SERVICE).count(),
    }
    
    # Count by status
    pages_by_status = {
        PAGE_STATUS_ACTIVE: all_pages.filter(status=PAGE_STATUS_ACTIVE).count(),
        PAGE_STATUS_DEACTIVATED: all_pages.filter(status=PAGE_STATUS_DEACTIVATED).count(),
        PAGE_STATUS_INVISIBLE: all_pages.filter(status=PAGE_STATUS_INVISIBLE).count(),
    }
    
    # Specific counts
    deactivated_pages_count = pages_by_status[PAGE_STATUS_DEACTIVATED]
    invisible_pages_count = pages_by_status[PAGE_STATUS_INVISIBLE]
    
    return {
        'total_pages': total_pages,
        'pages_by_type': pages_by_type,
        'pages_by_status': pages_by_status,
        'deactivated_pages_count': deactivated_pages_count,
        'invisible_pages_count': invisible_pages_count,
    }

