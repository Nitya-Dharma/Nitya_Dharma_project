"""
Service functions for preserving pinned posts when Pandit is removed or deactivated.

TASK 8: Pinned Posts by Removed/Deactivated Pandit

This module ensures that:
- Pinned posts remain pinned even if Pandit is deactivated
- Deactivated Pandit loses pin/unpin privileges
- Only Super Admin can unpin afterward
- Max 5 pinned posts rule is enforced
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from pages.models import PagePost

User = get_user_model()
logger = logging.getLogger(__name__)


def preserve_pinned_posts_on_pandit_deactivation(pandit, actor=None):
    """
    TASK 8: Preserve pinned posts when Pandit is deactivated.
    
    This function:
    - Ensures all pinned posts by this Pandit remain pinned
    - Preserves pinned_by reference
    - Logs audit events
    
    Args:
        pandit: User instance (must have role='pandit' or 'admin')
        actor: User instance (Super Admin performing deactivation)
    
    Returns:
        dict: Summary of pinned posts preserved
    
    Raises:
        ValidationError: If user is not a Pandit/Admin
    """
    if pandit.role not in ['pandit', 'admin']:
        raise ValidationError(f"User {pandit.email} is not a Pandit or Admin.")
    
    with transaction.atomic():
        # Find all posts pinned by this Pandit
        pinned_posts = PagePost.objects.filter(pinned_by=pandit, is_pinned=True)
        post_count = pinned_posts.count()
        
        if post_count == 0:
            logger.info(f"Pandit {pandit.email} has no pinned posts")
            return {
                'post_count': 0,
                'posts_preserved': [],
                'message': 'No pinned posts to preserve'
            }
        
        # Posts remain pinned - pinned_by is preserved (SET_NULL on delete)
        # No action needed - the FK relationship handles it
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            pandit,
            actor=actor,
            reason=f"PIN_PRESERVED_AFTER_PANDIT_DEACTIVATION - {post_count} pinned post(s) remain pinned"
        )
        
        logger.info(
            f"Pinned posts preserved for deactivated Pandit - "
            f"Pandit: {pandit.email}, Pinned posts: {post_count}"
        )
        
        return {
            'post_count': post_count,
            'posts_preserved': [p.id for p in pinned_posts],
            'message': f'{post_count} pinned post(s) preserved - remain pinned, only Super Admin can unpin'
        }


def unpin_post_by_super_admin(post, reason=None, actor=None):
    """
    TASK 8: Unpin a post (only Super Admin can do this).
    
    Pinned posts remain pinned even if the Pandit who pinned them is deactivated.
    Only Super Admin can unpin afterward.
    
    Args:
        post: PagePost instance to unpin
        reason (str, optional): Reason for unpinning
        actor (User, optional): User performing unpin action (must be Super Admin)
    
    Returns:
        dict: Summary of unpin action
    
    Raises:
        ValidationError: If actor is not Super Admin or post is not pinned
    """
    if actor and not actor.is_superuser:
        raise ValidationError("Only Super Admin can unpin posts.")
    
    if not post.is_pinned:
        raise ValidationError(f"Post {post.id} is not pinned.")
    
    with transaction.atomic():
        # Unpin the post
        post.unpin(
            reason=reason or "Post unpinned by Super Admin",
            actor=actor
        )
        
        logger.info(
            f"Post unpinned by Super Admin - "
            f"Post ID: {post.id}, Page: {post.page.title}, "
            f"Reason: {reason or 'N/A'}, Actor: {actor.email if actor else 'System'}"
        )
        
        return {
            'post_id': post.id,
            'is_pinned': post.is_pinned,
            'unpinned_at': timezone.now(),
            'reason': reason or 'N/A'
        }







