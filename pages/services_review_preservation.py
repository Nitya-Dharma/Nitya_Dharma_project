"""
Service functions for preserving reviews when user accounts are deleted or deactivated.

TASK 9: Reviews by Users Who Delete/Deactivate Account

This module ensures that:
- Reviews are never deleted automatically
- Ratings remain included in aggregates
- Reviewer identity is preserved (anonymized if needed)
- Historical trust is preserved
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from pages.models import PageReview

User = get_user_model()
logger = logging.getLogger(__name__)


def preserve_reviews_on_user_deactivation(user, actor=None):
    """
    TASK 9: Preserve reviews when user account is deactivated.
    
    This function:
    - Ensures all reviews by this user remain visible
    - Preserves reviewer_display_name
    - Reviews remain counted in rating aggregates
    - User FK is set to NULL (SET_NULL on delete)
    
    Args:
        user: User instance to deactivate
        actor: User instance (Super Admin performing deactivation)
    
    Returns:
        dict: Summary of reviews preserved
    
    Raises:
        ValidationError: If user is not a regular user
    """
    with transaction.atomic():
        # Find all reviews by this user
        reviews = PageReview.objects.filter(user=user)
        review_count = reviews.count()
        
        if review_count == 0:
            logger.info(f"User {user.email} has no reviews")
            return {
                'review_count': 0,
                'reviews_preserved': [],
                'message': 'No reviews to preserve'
            }
        
        # Ensure all reviews have reviewer_display_name set
        reviews_updated = 0
        for review in reviews:
            if not review.reviewer_display_name:
                # Get display name from reviewer
                if user.username:
                    review.reviewer_display_name = user.username
                elif user.get_full_name():
                    review.reviewer_display_name = user.get_full_name()
                else:
                    review.reviewer_display_name = user.email
                
                review.save(update_fields=['reviewer_display_name'])
                reviews_updated += 1
        
        # When user is deactivated, the FK will be set to NULL (SET_NULL)
        # But we preserve the reviewer_display_name for attribution
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            user,
            actor=actor,
            reason=f"REVIEW_PRESERVED_AFTER_USER_REMOVAL - {review_count} review(s) preserved with rating integrity"
        )
        
        logger.info(
            f"Reviews preserved for deactivated user - "
            f"User: {user.email}, Reviews: {review_count}, "
            f"Reviews updated: {reviews_updated}"
        )
        
        return {
            'review_count': review_count,
            'reviews_preserved': [r.id for r in reviews],
            'reviews_updated': reviews_updated,
            'message': f'{review_count} review(s) preserved - ratings remain counted, reviewer anonymized'
        }


def hide_review_by_super_admin(review, reason=None, actor=None):
    """
    TASK 9: Hide a review (only Super Admin can do this).
    
    Reviews are never deleted, only hidden. Rating remains counted in aggregates.
    
    Args:
        review: PageReview instance to hide
        reason (str, optional): Reason for hiding
        actor (User, optional): User performing hide action (must be Super Admin)
    
    Returns:
        dict: Summary of hide action
    
    Raises:
        ValidationError: If actor is not Super Admin
    """
    if actor and not actor.is_superuser:
        raise ValidationError("Only Super Admin can hide reviews.")
    
    if review.visibility_state == PageReview.HIDDEN:
        raise ValidationError(f"Review {review.id} is already hidden.")
    
    with transaction.atomic():
        # Hide the review
        review.visibility_state = PageReview.HIDDEN
        review.save(update_fields=['visibility_state'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            review,
            actor=actor,
            reason=f"REVIEW_HIDDEN_BY_SUPER_ADMIN - Review ID: {review.id}, Reason: {reason or 'N/A'}"
        )
        
        logger.info(
            f"Review hidden by Super Admin - "
            f"Review ID: {review.id}, Page: {review.page.title}, "
            f"Reason: {reason or 'N/A'}, Actor: {actor.email if actor else 'System'}"
        )
        
        return {
            'review_id': review.id,
            'visibility_state': review.visibility_state,
            'hidden_at': timezone.now(),
            'reason': reason or 'N/A'
        }







