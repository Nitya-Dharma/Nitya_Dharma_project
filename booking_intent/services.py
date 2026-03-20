"""
Booking Intent Service

Task 8.10: Booking Intent Service Layer
Task 8.11: Booking Intent Validation & Business Rules

Service layer for booking intent operations.
Read-only queries and controlled mutations only.
"""

import logging
from typing import Optional, List
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import BookingIntent

User = get_user_model()
logger = logging.getLogger(__name__)


class BookingIntentService:
    """
    Service for booking intent operations.
    
    All methods follow strict business rules.
    No side effects beyond booking intent records.
    """
    
    @staticmethod
    @transaction.atomic
    def create_intent(
        requester: User,
        pandit_id: int,
        optional_requested_date: Optional[str] = None,
        optional_requested_time: Optional[str] = None,
        message: Optional[str] = None,
        user_mobile_number: Optional[str] = None
    ) -> BookingIntent:
        """
        Create a new booking intent.
        
        Args:
            requester: User creating the intent
            pandit_id: ID of the Pandit
            optional_requested_date: Optional date (YYYY-MM-DD)
            optional_requested_time: Optional time (HH:MM:SS)
            message: Optional message text
            user_mobile_number: Mobile number provided by user (required)
        
        Returns:
            Created BookingIntent instance
        """
        # Get Pandit user
        try:
            pandit = User.objects.get(id=pandit_id, role='pandit', status='active', is_active=True)
        except User.DoesNotExist:
            raise ValueError(f"Pandit with id {pandit_id} not found or not active")
        
        # Parse date if provided
        parsed_date = None
        if optional_requested_date:
            from django.utils.dateparse import parse_date
            parsed_date = parse_date(optional_requested_date)
            if parsed_date is None:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
        
        # Parse time if provided
        parsed_time = None
        if optional_requested_time:
            from django.utils.dateparse import parse_time
            parsed_time = parse_time(optional_requested_time)
            if parsed_time is None:
                raise ValueError("Invalid time format. Use HH:MM:SS")
        
        # Validate mobile number (required)
        if not user_mobile_number or not user_mobile_number.strip():
            raise ValueError("Mobile number is required. Please add your mobile number so the Pandit can contact you.")
        
        user_mobile_number = user_mobile_number.strip()
        if len(user_mobile_number) > 15:
            raise ValueError("Mobile number must be 15 characters or less")
        
        # Create booking intent
        intent = BookingIntent.objects.create(
            requester=requester,
            pandit=pandit,
            optional_requested_date=parsed_date,
            optional_requested_time=parsed_time,
            message=message,
            user_mobile_number=user_mobile_number,
            status=BookingIntent.STATUS_SUBMITTED,
            created_by=requester  # User who created the booking intent
        )
        
        # Store audit snapshots
        intent.requester_status_at_creation = requester.status
        intent.pandit_status_at_creation = pandit.status
        intent.save(update_fields=['requester_status_at_creation', 'pandit_status_at_creation'])
        
        logger.info(f"Booking intent {intent.id} created by {requester.email} for Pandit {pandit.email}")
        
        return intent
    
    @staticmethod
    def get_intents_for_requester(requester: User, status: Optional[str] = None):
        """
        Get all booking intents created by a requester.
        
        Args:
            requester: User who created the intents
            status: Optional status filter
        
        Returns:
            QuerySet of BookingIntent instances (ordered by -created_at)
        """
        queryset = BookingIntent.objects.filter(requester=requester)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related('requester', 'pandit').order_by('-created_at')
    
    @staticmethod
    def get_intents_for_pandit(pandit: User, status: Optional[str] = None):
        """
        Get all booking intents received by a Pandit.
        
        Args:
            pandit: Pandit user
            status: Optional status filter
        
        Returns:
            QuerySet of BookingIntent instances (ordered by -created_at)
        """
        queryset = BookingIntent.objects.filter(pandit=pandit)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.select_related('requester', 'pandit').order_by('-created_at')
    
    @staticmethod
    @transaction.atomic
    def cancel_intent(intent_id: int, user: User) -> BookingIntent:
        """
        Cancel a booking intent.
        
        TASK 21, 22: Pandit can close intents even if requester is deactivated.
        
        Args:
            intent_id: ID of the intent to cancel
            user: User cancelling the intent (must be requester or pandit)
        
        Returns:
            Updated BookingIntent instance
        """
        try:
            intent = BookingIntent.objects.get(id=intent_id)
        except BookingIntent.DoesNotExist:
            raise ValueError(f"Booking intent {intent_id} not found")
        
        # TASK 21: Check if intent is read-only (closed by system)
        if intent.status == BookingIntent.STATUS_CLOSED_SYSTEM:
            raise ValueError("Intent is closed by system and cannot be cancelled")
        
        # Check permissions
        if intent.requester != user and intent.pandit != user:
            raise PermissionError("Only requester or pandit can cancel this intent")
        
        # TASK 22: Allow Pandit to close even if requester is deactivated
        if intent.pandit == user:
            # Pandit can always close intents addressed to them
            pass
        elif intent.requester == user:
            # Requester can only cancel if they are active
            if not user.is_active or user.status == 'deactivated':
                raise PermissionError("Deactivated users cannot cancel intents")
        
        # Check if already cancelled
        if intent.status == BookingIntent.STATUS_CANCELLED:
            raise ValueError("Intent is already cancelled")
        
        # PART 3 HARDENING: Explicit state transition validation
        from core.api_constants import BOOKING_INTENT_STATUS_TRANSITIONS
        current_state = intent.status
        new_state = BookingIntent.STATUS_CANCELLED
        
        # Validate transition is allowed
        allowed_next_states = BOOKING_INTENT_STATUS_TRANSITIONS.get(current_state, [])
        if new_state not in allowed_next_states:
            raise ValueError(f"Invalid state transition: {current_state} -> {new_state}")
        
        # Update status
        intent.status = new_state
        intent.updated_by = user
        intent.save(update_fields=['status', 'updated_at', 'updated_by'])
        
        logger.info(f"Booking intent {intent_id} cancelled by {user.email}")
        
        return intent
    
    @staticmethod
    @transaction.atomic
    def mark_as_viewed(intent_id: int, user: User) -> BookingIntent:
        """
        Mark a booking intent as viewed by Pandit.
        
        Args:
            intent_id: ID of the intent
            user: Pandit user viewing the intent
        
        Returns:
            Updated BookingIntent instance
        """
        try:
            intent = BookingIntent.objects.get(id=intent_id, pandit=user)
        except BookingIntent.DoesNotExist:
            raise ValueError(f"Booking intent {intent_id} not found or user is not the Pandit")
        
        # Update status if still submitted
        if intent.status == BookingIntent.STATUS_SUBMITTED:
            intent.status = BookingIntent.STATUS_VIEWED
            intent.updated_by = user
            intent.save(update_fields=['status', 'updated_at', 'updated_by'])
        
        return intent
    
    @staticmethod
    def get_all_intents_for_governance(status=None, is_flagged=None):
        """
        Get booking intents for governance/admin review.
        
        Args:
            status: Optional status filter (e.g. from STATUS_CHOICES).
            is_flagged: Optional bool to filter by is_flagged.
        
        Returns:
            QuerySet of BookingIntent (allows DB-level pagination in the view).
        """
        qs = (
            BookingIntent.objects.all()
            .select_related("requester", "pandit")
            .order_by("-created_at")
        )
        if status is not None:
            qs = qs.filter(status=status)
        if is_flagged is not None:
            qs = qs.filter(is_flagged=is_flagged)
        return qs
    
    @staticmethod
    @transaction.atomic
    def flag_intent(intent_id: int, reason: str, user: User) -> BookingIntent:
        """
        Flag a booking intent for governance review.
        
        Args:
            intent_id: ID of the intent to flag
            reason: Reason for flagging
            user: User flagging the intent
        
        Returns:
            Updated BookingIntent instance
        """
        try:
            intent = BookingIntent.objects.get(id=intent_id)
        except BookingIntent.DoesNotExist:
            raise ValueError(f"Booking intent {intent_id} not found")
        
        # Set flagged status
        intent.is_flagged = True
        intent.flagged_reason = reason
        intent.flagged_at = timezone.now()
        intent.updated_by = user
        intent.save(update_fields=['is_flagged', 'flagged_reason', 'flagged_at', 'updated_at', 'updated_by'])
        
        logger.info(f"Booking intent {intent_id} flagged by {user.email}: {reason}")
        
        return intent
