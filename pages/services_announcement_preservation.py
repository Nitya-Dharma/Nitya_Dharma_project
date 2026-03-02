"""
Service functions for preserving announcements created by removed Admin Pandits.

TASK 27: System Announcements Created by Removed Admin

This module ensures that:
- Announcements remain visible when author is deactivated
- Original author attribution is preserved
- Author status is shown as Inactive
- Only Super Admin can edit/hide legacy announcements
"""

import logging
from django.contrib.auth import get_user_model
from .models import PagePost

User = get_user_model()
logger = logging.getLogger(__name__)


def get_author_display_name(post: PagePost) -> str:
    """
    TASK 27: Get display name for post author, handling deactivated users.
    
    Args:
        post: PagePost instance
    
    Returns:
        str: Display name for author
    """
    # If author is active, use current name
    if post.created_by.is_active and post.created_by.status != 'deactivated':
        return post.created_by.get_full_name() or post.created_by.email
    
    # If author is deactivated, use immutable snapshot
    if post.created_by_display_name:
        return f"{post.created_by_display_name} (Inactive)"
    
    # Fallback to email if display name not set
    return f"{post.created_by.email} (Inactive)"


def can_edit_announcement(post: PagePost, user: User) -> bool:
    """
    TASK 27: Check if user can edit an announcement.
    
    Rules:
    - Inactive Admin Pandit: no access
    - Other Admin Pandits: cannot edit
    - Super Admin: can hide, cannot delete
    
    Args:
        post: PagePost instance
        user: User attempting to edit
    
    Returns:
        bool: True if user can edit
    """
    # Super Admin can hide announcements
    if user.is_superuser:
        return True
    
    # Original author can edit if still active
    if post.created_by == user:
        if user.is_active and user.status != 'deactivated':
            return True
    
    # No one else can edit
    return False


def can_hide_announcement(post: PagePost, user: User) -> bool:
    """
    TASK 27: Check if user can hide an announcement.
    
    Only Super Admin can hide announcements.
    
    Args:
        post: PagePost instance
        user: User attempting to hide
    
    Returns:
        bool: True if user can hide
    """
    return user.is_superuser


def hide_announcement(post: PagePost, user: User, reason: str = None):
    """
    TASK 27: Hide an announcement (Super Admin only).
    
    Args:
        post: PagePost instance
        user: User hiding the announcement (must be Super Admin)
        reason: Optional reason for hiding
    
    Returns:
        PagePost: Updated post instance
    """
    if not user.is_superuser:
        raise PermissionError("Only Super Admin can hide announcements")
    
    post.status = PagePost.POST_STATUS_HIDDEN
    post.is_hidden = True
    post.save(update_fields=['status', 'is_hidden', 'updated_at'])
    
    # Log audit event
    try:
        from core.audit import log_deactivation
        log_deactivation(
            post,
            actor=user,
            reason=f"ANNOUNCEMENT_HIDDEN - {reason or 'Hidden by Super Admin'}"
        )
    except Exception:
        pass
    
    logger.info(f"TASK 27: Announcement {post.id} hidden by Super Admin {user.email}")
    
    return post







