"""
Review Permissions

Task 9.4: Review Visibility & Access Rules

Permission checks for review operations.
Read-only checks, no mutations, no side effects.
"""

from django.contrib.auth import get_user_model
from .models import Review

User = get_user_model()


def can_create_review(user: User) -> bool:
    """
    Check if user can create a review.
    
    Rules:
    - User must be authenticated
    - User must have role='user' (end users only)
    - User must have active status
    - Pandits cannot create reviews (they receive them)
    
    Args:
        user: User to check
    
    Returns:
        True if user can create review, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Only regular users (end users) can create reviews
    # Pandits receive reviews, they don't create them
    return user.role == 'user' and user.status == 'active' and user.is_active


def can_view_review(user: User, review: Review) -> bool:
    """
    Check if user can view a review.
    
    Rules:
    - Public reviews (visible state) can be viewed by anyone
    - Reviewer can view their own reviews (any state)
    - Pandit can view reviews about them (any state)
    - Admins can view all reviews (any state)
    
    Args:
        user: User to check (can be None for anonymous)
        review: Review instance
    
    Returns:
        True if user can view review, False otherwise
    """
    # Visible reviews can be viewed by anyone (including anonymous)
    if review.visibility_state == Review.VISIBLE:
        return True
    
    # If review is not visible, check if user has special access
    if not user or not user.is_authenticated:
        return False
    
    # Reviewer can view their own reviews (any state)
    if review.user == user:
        return True
    
    # Pandit can view reviews about them (any state)
    if review.pandit == user:
        return True
    
    # Admins can view all reviews (any state)
    if user.is_staff or user.is_superuser or user.role == 'admin':
        return True
    
    return False


def can_change_visibility(user: User) -> bool:
    """
    Check if user can change review visibility state.
    
    Rules:
    - Only admins can change visibility (governance action)
    - This is an admin-only operation
    
    Args:
        user: User to check
    
    Returns:
        True if user can change visibility, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Only admins can change visibility (governance action)
    return user.is_staff or user.is_superuser or user.role == 'admin'
