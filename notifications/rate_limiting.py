"""
Notification Rate Limiting — PART 5 — PRODUCTION READINESS

TASK 5.7: Notification Rate Limits

Add hard rate limits for notifications to prevent spam.

RULES:
- Same notification type → max 1 per X minutes
- Bulk notifications batched
- No retry storms
"""

from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


# Rate limit configuration (in minutes)
RATE_LIMITS = {
    'booking_intent_received': 5,  # Max 1 per 5 minutes
    'booking_intent_accepted': 5,
    'booking_intent_rejected': 5,
    'review_received': 10,  # Max 1 per 10 minutes
    'page_post_created': 15,  # Max 1 per 15 minutes
    'follower_added': 30,  # Max 1 per 30 minutes
    'default': 5,  # Default rate limit
}


def check_rate_limit(recipient_id, notification_type, source_module=None):
    """
    Check if notification can be sent based on rate limits.
    
    Args:
        recipient_id: User ID of recipient
        notification_type: Type of notification
        source_module: Optional source module
    
    Returns:
        tuple: (allowed: bool, reason: str)
    """
    # Get rate limit for this notification type
    rate_limit_minutes = RATE_LIMITS.get(notification_type, RATE_LIMITS['default'])
    
    # Create cache key
    cache_key = f"notification_rate_limit:{recipient_id}:{notification_type}"
    
    # Check if notification was sent recently
    last_sent = cache.get(cache_key)
    
    if last_sent:
        # Check if rate limit period has passed
        time_since_last = timezone.now() - last_sent
        if time_since_last < timedelta(minutes=rate_limit_minutes):
            remaining_seconds = (timedelta(minutes=rate_limit_minutes) - time_since_last).total_seconds()
            return False, f"Rate limit: Please wait {int(remaining_seconds)} seconds before sending another {notification_type} notification"
    
    # Rate limit passed - allow notification
    return True, "Rate limit passed"


def record_notification_sent(recipient_id, notification_type):
    """
    Record that a notification was sent (for rate limiting).
    
    Args:
        recipient_id: User ID of recipient
        notification_type: Type of notification
    """
    rate_limit_minutes = RATE_LIMITS.get(notification_type, RATE_LIMITS['default'])
    cache_key = f"notification_rate_limit:{recipient_id}:{notification_type}"
    
    # Store timestamp in cache (expires after rate limit period)
    cache.set(cache_key, timezone.now(), timeout=rate_limit_minutes * 60)


def check_duplicate_notification(recipient_id, notification_type, source_module, payload_hash=None):
    """
    Check if a duplicate notification already exists.
    
    Args:
        recipient_id: User ID of recipient
        notification_type: Type of notification
        source_module: Source module
        payload_hash: Optional hash of payload for duplicate detection
    
    Returns:
        bool: True if duplicate exists
    """
    from .models import Notification
    
    # Check for recent duplicate (within last hour)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    
    query = Notification.objects.filter(
        recipient_id=recipient_id,
        notification_type=notification_type,
        source_module=source_module,
        created_at__gte=one_hour_ago,
    )
    
    # If payload hash provided, check for exact duplicate
    if payload_hash:
        # Note: This requires payload_hash field in Notification model
        # For now, we check by type and time window
        pass
    
    return query.exists()


def should_send_notification(recipient_id, notification_type, source_module, payload_hash=None):
    """
    Determine if notification should be sent (checks rate limit and duplicates).
    
    Args:
        recipient_id: User ID of recipient
        notification_type: Type of notification
        source_module: Source module
        payload_hash: Optional hash of payload
    
    Returns:
        tuple: (should_send: bool, reason: str)
    """
    # Check rate limit
    rate_allowed, rate_reason = check_rate_limit(recipient_id, notification_type, source_module)
    if not rate_allowed:
        logger.info(f"Notification rate limited: {rate_reason}")
        return False, rate_reason
    
    # Check for duplicates
    if check_duplicate_notification(recipient_id, notification_type, source_module, payload_hash):
        logger.info(f"Duplicate notification detected: {notification_type} for user {recipient_id}")
        return False, "Duplicate notification detected"
    
    return True, "Notification allowed"


def create_notification_with_rate_limit(recipient, notification_type, source_module, **kwargs):
    """
    Create notification with rate limiting and duplicate checking.
    
    Args:
        recipient: User instance
        notification_type: Type of notification
        source_module: Source module
        **kwargs: Additional Notification model fields
    
    Returns:
        tuple: (notification: Notification or None, created: bool, reason: str)
    """
    from .models import Notification
    
    # Check if should send
    should_send, reason = should_send_notification(
        recipient.id,
        notification_type,
        source_module
    )
    
    if not should_send:
        return None, False, reason
    
    # Create notification
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        source_module=source_module,
        **kwargs
    )
    
    # Record that notification was sent
    record_notification_sent(recipient.id, notification_type)
    
    logger.info(f"Notification created: {notification_type} for user {recipient.id}")
    
    return notification, True, "Notification created successfully"




