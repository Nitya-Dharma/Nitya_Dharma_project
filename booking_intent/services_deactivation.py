"""
Service functions for handling booking intents when Pandits or Users are deactivated.

TASK 21: Booking Intents Sent to Deactivated Pandit
TASK 22: Booking Intents Sent by Deactivated User
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import BookingIntent

User = get_user_model()
logger = logging.getLogger(__name__)


def handle_pandit_deactivation_booking_intents(pandit, actor=None):
    """
    TASK 21: Handle booking intents when Pandit is deactivated.
    
    Auto-closes all OPEN intents (submitted/viewed) and sets status to CLOSED_SYSTEM.
    
    Args:
        pandit: User instance (must be Pandit)
        actor: User who deactivated the Pandit (optional)
    
    Returns:
        dict: Summary of actions taken
    """
    with transaction.atomic():
        # Find all OPEN intents (submitted or viewed, not cancelled/expired/closed)
        open_intents = BookingIntent.objects.filter(
            pandit=pandit,
            status__in=[BookingIntent.STATUS_SUBMITTED, BookingIntent.STATUS_VIEWED]
        )
        
        intent_count = open_intents.count()
        
        if intent_count > 0:
            # Update all open intents to CLOSED_SYSTEM
            open_intents.update(
                status=BookingIntent.STATUS_CLOSED_SYSTEM,
                updated_at=timezone.now()
            )
            
            # Log audit event
            try:
                from core.audit import log_deactivation
                log_deactivation(
                    pandit,
                    actor=actor,
                    reason=f"BOOKING_INTENT_AUTO_CLOSED - {intent_count} intent(s) auto-closed due to Pandit deactivation"
                )
            except Exception:
                pass
            
            logger.info(
                f"TASK 21: Auto-closed {intent_count} booking intent(s) for deactivated Pandit {pandit.email}"
            )
        
        return {
            'intents_closed': intent_count,
            'pandit_id': pandit.id,
            'pandit_email': pandit.email
        }


def get_requester_display_name(intent: BookingIntent) -> str:
    """
    TASK 22: Get display name for requester, handling deactivated users.
    
    Args:
        intent: BookingIntent instance
    
    Returns:
        str: Display name for requester
    """
    # If requester is active, use current name
    if intent.requester.is_active and intent.requester.status != 'deactivated':
        return intent.requester.get_full_name() or intent.requester.email
    
    # If requester is deactivated, use immutable snapshot
    if intent.requester_display_name:
        return f"{intent.requester_display_name} (Inactive User)"
    
    # Fallback to email if display name not set
    return f"{intent.requester.email} (Inactive User)"


def can_pandit_close_intent(intent: BookingIntent, pandit: User) -> bool:
    """
    TASK 22: Check if Pandit can close a booking intent (even if requester is deactivated).
    
    Args:
        intent: BookingIntent instance
        pandit: Pandit user
    
    Returns:
        bool: True if Pandit can close the intent
    """
    # Pandit can always close intents addressed to them, regardless of requester status
    return intent.pandit == pandit


def is_intent_read_only(intent: BookingIntent) -> bool:
    """
    TASK 21: Check if booking intent is read-only (closed by system).
    
    Args:
        intent: BookingIntent instance
    
    Returns:
        bool: True if intent is read-only
    """
    return intent.status == BookingIntent.STATUS_CLOSED_SYSTEM


def get_intent_user_message(intent: BookingIntent) -> Optional[str]:
    """
    TASK 21: Get user-facing message for booking intent status.
    
    Args:
        intent: BookingIntent instance
    
    Returns:
        str: User message or None
    """
    if intent.status == BookingIntent.STATUS_CLOSED_SYSTEM:
        return "The Pandit is no longer available. This request has been closed."
    
    return None







