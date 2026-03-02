"""
Notification Contracts

Task 17.2: Notification Types Classification
Task 17.4: Notification Event Contracts

Defines notification event validation and contracts.
"""

from typing import Optional, Dict, Any
from .constants import (
    NOTIFICATION_TYPE_CHOICES,
    NOTIFICATION_TYPE_SYSTEM,
    NOTIFICATION_TYPE_GOVERNANCE,
    NOTIFICATION_TYPE_PAGE_UPDATE,
    NOTIFICATION_TYPE_BOOKING_INTENT,
    NOTIFICATION_TYPE_REVIEW,
)


def create_notification_event(
    notification_type: str,
    source_module: str,
    payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Create and validate a notification event.
    
    Args:
        notification_type: Type of notification (must be in NOTIFICATION_TYPE_CHOICES)
        source_module: Module that triggered the notification
        payload: Notification payload (must be safe, no PII)
    
    Returns:
        Validated event dict or None if invalid
    """
    # Validate notification type
    valid_types = [choice[0] for choice in NOTIFICATION_TYPE_CHOICES]
    if notification_type not in valid_types:
        return None
    
    # Validate payload is a dict
    if not isinstance(payload, dict):
        return None
    
    # Return validated event
    return {
        'notification_type': notification_type,
        'source_module': source_module,
        'payload': payload,
    }
