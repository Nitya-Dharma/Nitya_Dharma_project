"""
Booking Intent Permissions

Task 8.5: Booking Intent Permission Rules

Permission checks for booking intent operations.
Read-only checks, no mutations, no side effects.
"""

from typing import Optional
from django.contrib.auth import get_user_model
from .models import BookingIntent

User = get_user_model()


def can_create_intent(user: User) -> bool:
    """
    Check if user can create a booking intent.
    
    Rules:
    - User must be authenticated
    - User must have role='user' (end users only)
    - Pandits cannot create intents (they receive them)
    
    Args:
        user: User to check
    
    Returns:
        True if user can create intent, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Only regular users (end users) can create intents
    # Pandits receive intents, they don't create them
    return user.role == 'user' and user.status == 'active' and user.is_active


def can_view_intent(user: User, intent: BookingIntent) -> bool:
    """
    Check if user can view a booking intent.
    
    Rules:
    - Requester can view their own intents
    - Pandit can view intents addressed to them
    - Admins can view all intents
    
    Args:
        user: User to check
        intent: BookingIntent instance
    
    Returns:
        True if user can view intent, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Requester can view their own intents
    if intent.requester == user:
        return True
    
    # Pandit can view intents addressed to them
    if intent.pandit == user:
        return True
    
    # Admins can view all intents
    if user.is_staff or user.is_superuser or user.role == 'admin':
        return True
    
    return False


def can_cancel_intent(user: User, intent: BookingIntent) -> bool:
    """
    Check if user can cancel a booking intent.
    
    Rules:
    - Requester can cancel their own intents
    - Pandit can cancel intents addressed to them
    - Admins can cancel any intent
    
    Args:
        user: User to check
        intent: BookingIntent instance
    
    Returns:
        True if user can cancel intent, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Requester can cancel their own intents
    if intent.requester == user:
        return True
    
    # Pandit can cancel intents addressed to them
    if intent.pandit == user:
        return True
    
    # Admins can cancel any intent
    if user.is_staff or user.is_superuser or user.role == 'admin':
        return True
    
    return False


def can_mark_as_viewed(user: User, intent: BookingIntent) -> bool:
    """
    Check if user can mark a booking intent as viewed.
    
    Rules:
    - Only the Pandit (recipient) can mark intents as viewed
    - Admins can mark any intent as viewed
    
    Args:
        user: User to check
        intent: BookingIntent instance
    
    Returns:
        True if user can mark intent as viewed, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Pandit can mark intents addressed to them as viewed
    if intent.pandit == user:
        return True
    
    # Admins can mark any intent as viewed
    if user.is_staff or user.is_superuser or user.role == 'admin':
        return True
    
    return False


def can_flag_intent(user: User, intent: Optional[BookingIntent] = None) -> bool:
    """
    Check if user can flag a booking intent for governance review.
    
    Rules:
    - Only admins can flag intents (governance action)
    - This is an admin-only operation
    
    Args:
        user: User to check
        intent: Optional BookingIntent instance (not used, kept for compatibility)
    
    Returns:
        True if user can flag intent, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    # Only admins can flag intents (governance action)
    return user.is_staff or user.is_superuser or user.role == 'admin'
