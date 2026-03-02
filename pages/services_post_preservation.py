"""
Service functions for preserving posts created by deactivated Admin Pandits.

TASK 7: Posts Created by Deactivated Admin Pandit

This module ensures that:
- Posts are never deleted automatically when Admin Pandit is deactivated
- Authorship attribution is preserved
- Engagement history remains intact
- Posts remain visible by default
- Super Admin can hide posts (not delete)
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from pages.models import PagePost

User = get_user_model()
logger = logging.getLogger(__name__)


def handle_admin_pandit_post_preservation(admin_pandit, actor=None):
    """
    TASK 7: Preserve posts created by deactivated Admin Pandit.
    
    This function:
    - Ensures all posts created by Admin Pandit remain visible
    - Preserves created_by and created_by_display_name
    - Does NOT delete or hide posts automatically
    - Logs audit events
    
    Args:
        admin_pandit: User instance (must have role='admin')
        actor: User instance (Super Admin performing deactivation)
    
    Returns:
        dict: Summary of posts preserved
    
    Raises:
        ValidationError: If user is not an Admin Pandit
    """
    if admin_pandit.role != 'admin':
        raise ValidationError(f"User {admin_pandit.email} is not an Admin Pandit.")
    
    with transaction.atomic():
        # Find all posts created by this Admin Pandit
        posts = PagePost.objects.filter(created_by=admin_pandit)
        post_count = posts.count()
        
        if post_count == 0:
            logger.info(f"Admin Pandit {admin_pandit.email} created no posts")
            return {
                'post_count': 0,
                'posts_preserved': [],
                'message': 'No posts to preserve'
            }
        
        # Ensure all posts have created_by_display_name set
        posts_updated = 0
        for post in posts:
            if not post.created_by_display_name:
                # Get display name from creator
                if admin_pandit.username:
                    post.created_by_display_name = admin_pandit.username
                elif admin_pandit.get_full_name():
                    post.created_by_display_name = admin_pandit.get_full_name()
                else:
                    post.created_by_display_name = admin_pandit.email
                
                post.save(update_fields=['created_by_display_name'])
                posts_updated += 1
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            admin_pandit,
            actor=actor,
            reason=f"ADMIN_PANDIT_DEACTIVATED - {post_count} post(s) preserved with attribution intact"
        )
        
        logger.info(
            f"Posts preserved for deactivated Admin Pandit - "
            f"Admin: {admin_pandit.email}, Posts: {post_count}, "
            f"Posts updated: {posts_updated}"
        )
        
        return {
            'post_count': post_count,
            'posts_preserved': [p.id for p in posts],
            'posts_updated': posts_updated,
            'message': f'{post_count} post(s) preserved with attribution intact'
        }


def hide_post_by_super_admin(post, reason=None, actor=None):
    """
    TASK 7: Hide a post (only Super Admin can do this).
    
    Posts are never deleted, only hidden. Attribution is preserved.
    
    Args:
        post: PagePost instance to hide
        reason (str, optional): Reason for hiding
        actor (User, optional): User performing hide action (must be Super Admin)
    
    Returns:
        dict: Summary of hide action
    
    Raises:
        ValidationError: If actor is not Super Admin
    """
    if actor and not actor.is_superuser:
        raise ValidationError("Only Super Admin can hide posts.")
    
    if post.status == PagePost.POST_STATUS_HIDDEN:
        raise ValidationError(f"Post {post.id} is already hidden.")
    
    with transaction.atomic():
        # Hide the post
        post.hide(
            reason=reason or "Post hidden by Super Admin",
            actor=actor
        )
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            post,
            actor=actor,
            reason=f"POST_HIDDEN_BY_SUPER_ADMIN - Post ID: {post.id}, Reason: {reason or 'N/A'}"
        )
        
        logger.info(
            f"Post hidden by Super Admin - "
            f"Post ID: {post.id}, Page: {post.page.title}, "
            f"Reason: {reason or 'N/A'}, Actor: {actor.email if actor else 'System'}"
        )
        
        return {
            'post_id': post.id,
            'status': post.status,
            'hidden_at': timezone.now(),
            'reason': reason or 'N/A'
        }







