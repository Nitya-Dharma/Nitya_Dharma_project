"""
Notification Services

Task 17.3: User Roles & Notification Eligibility Rules
Task 17.5: Page Follow & Event Notification Rules
Task 17.6: Booking Intent Notification Rules
Task 17.7: Review & Interaction Notification Rules
Task 17.8: Governance & Moderation Notification Rules
Task 17.10: Notification Visibility, Read State & Expiry

Service-layer functions for notification operations.
Delivery-only, no business logic, no authority.
"""

import logging
from typing import List, Optional, Dict, Any
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import Notification, NotificationPreference
from .constants import (
    NOTIFICATION_TYPE_SYSTEM,
    NOTIFICATION_TYPE_GOVERNANCE,
    NOTIFICATION_TYPE_PAGE_UPDATE,
    NOTIFICATION_TYPE_BOOKING_INTENT,
    NOTIFICATION_TYPE_REVIEW,
    NOTIFICATION_TYPE_PAGE_MODERATOR_ASSIGNED,
    NOTIFICATION_TYPE_TEMPLE_ANNOUNCEMENT,
)
from .contracts import create_notification_event

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for notification operations.
    
    All methods are delivery-only.
    No business logic, no ranking, no trust, no analytics.
    """
    
    @staticmethod
    def is_eligible_for_notification(
        user: User,
        notification_type: str
    ) -> bool:
        """
        Check if a user is eligible to receive a notification type.
        
        Task 17.3: User Roles & Notification Eligibility Rules
        
        Args:
            user: User instance
            notification_type: Type of notification
            
        Returns:
            bool: True if eligible, False otherwise
        """
        # System notifications: all authenticated users
        if notification_type == NOTIFICATION_TYPE_SYSTEM:
            return user.is_authenticated
        
        # Governance notifications: affected users and admins
        if notification_type == NOTIFICATION_TYPE_GOVERNANCE:
            return user.is_authenticated and user.role in ['pandit', 'admin']
        
        # Page update notifications: followers only
        if notification_type == NOTIFICATION_TYPE_PAGE_UPDATE:
            return user.is_authenticated  # Eligibility checked at delivery time
        
        # Booking intent notifications: participants only
        if notification_type == NOTIFICATION_TYPE_BOOKING_INTENT:
            return user.is_authenticated
        
        # Review notifications: Pandits and admins
        if notification_type == NOTIFICATION_TYPE_REVIEW:
            return user.is_authenticated and user.role in ['pandit', 'admin']
        
        # Page moderator assigned: Pandits only
        if notification_type == NOTIFICATION_TYPE_PAGE_MODERATOR_ASSIGNED:
            return user.is_authenticated and user.role == 'pandit'
        
        # Temple announcement notifications: all authenticated users
        if notification_type == NOTIFICATION_TYPE_TEMPLE_ANNOUNCEMENT:
            return user.is_authenticated
        
        return False
    
    @staticmethod
    def create_notification(
        recipient: User,
        notification_type: str,
        source_module: str,
        payload: Dict[str, Any],
        expires_at: Optional[timezone.datetime] = None,
        page=None,  # Optional: for temple-scoped notifications
    ) -> Optional[Notification]:
        """
        Create a notification.
        
        Validates eligibility, preferences, and payload safety.
        Best-effort delivery only.
        
        Args:
            recipient: User receiving the notification
            notification_type: Type of notification
            source_module: Source module identifier
            payload: Notification payload (must be safe)
            expires_at: Optional expiry timestamp
            
        Returns:
            Notification instance or None if creation failed
        """
        # Validate event
        event = create_notification_event(notification_type, source_module, payload)
        if not event:
            logger.warning(f"Invalid notification event: {notification_type} from {source_module}")
            return None
        
        # Check eligibility
        if not NotificationService.is_eligible_for_notification(recipient, notification_type):
            logger.debug(f"User {recipient.id} not eligible for {notification_type}")
            return None
        
        # Check user preferences (for optional notifications only)
        if not NotificationService._should_deliver_notification(recipient, notification_type):
            logger.debug(f"Notification suppressed by user preference: {notification_type}")
            return None
        
        # Create notification
        try:
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                source_module=source_module,
                payload=payload,
                expires_at=expires_at,
                page=page,  # Temple-scoped notifications
            )
            logger.info(f"Notification {notification.id} created for {recipient.email}")
            return notification
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return None
    
    @staticmethod
    def _should_deliver_notification(user: User, notification_type: str) -> bool:
        """
        Check if notification should be delivered based on user preferences.
        
        Mandatory notifications (governance, security) always bypass preferences.
        
        Args:
            user: User instance
            notification_type: Type of notification
            
        Returns:
            bool: True if should deliver, False otherwise
        """
        # Mandatory notifications always delivered
        if notification_type in [NOTIFICATION_TYPE_GOVERNANCE, NOTIFICATION_TYPE_SYSTEM]:
            return True
        
        # Get user preferences
        try:
            prefs = NotificationPreference.objects.get(user=user)
        except NotificationPreference.DoesNotExist:
            # Default: deliver all optional notifications
            return True
        
        # Check category preferences
        if notification_type == NOTIFICATION_TYPE_PAGE_UPDATE:
            return prefs.page_updates_enabled
        if notification_type == NOTIFICATION_TYPE_REVIEW:
            return prefs.review_notifications_enabled
        if notification_type == NOTIFICATION_TYPE_BOOKING_INTENT:
            return prefs.booking_intent_enabled
        
        # Default: deliver
        return True
    
    @staticmethod
    def mark_as_read(notification: Notification, user: User) -> bool:
        """
        Mark a notification as read.
        
        Task 17.10: Notification Visibility, Read State & Expiry
        
        Args:
            notification: Notification instance
            user: User marking as read (must be recipient)
            
        Returns:
            bool: True if marked, False otherwise
        """
        if notification.recipient != user:
            return False
        
        if notification.is_read:
            return True
        
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
        
        return True
    
    @staticmethod
    def mark_all_as_read(user: User) -> int:
        """
        Mark all unread notifications as read for a user.
        
        Args:
            user: User instance
            
        Returns:
            int: Number of notifications marked as read
        """
        count = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return count
    
    @staticmethod
    def get_user_notifications(
        user: User,
        limit: int = 20,
        unread_only: bool = False
    ) -> List[Notification]:
        """
        Get notifications for a user.
        
        Task 17.10: Notification Visibility, Read State & Expiry
        
        Args:
            user: User instance
            limit: Maximum number of notifications to return
            unread_only: If True, return only unread notifications
            
        Returns:
            List of Notification instances (chronological order)
        """
        queryset = Notification.objects.filter(recipient=user)
        
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        # Filter expired notifications
        from django.db.models import Q
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        return list(queryset.order_by('-created_at')[:limit])
    
    @staticmethod
    def notify_page_followers(
        page,
        notification_type: str,
        payload: Dict[str, Any]
    ) -> int:
        """
        Notify all followers of a Page.
        
        Task 17.5: Page Follow & Event Notification Rules
        EXTENDED: Now uses generic Follow model for temple notifications
        
        Args:
            page: Page instance
            notification_type: Type of notification (must be PAGE_UPDATE)
            payload: Notification payload
            
        Returns:
            int: Number of notifications created
        """
        if notification_type != NOTIFICATION_TYPE_PAGE_UPDATE:
            logger.warning(f"Invalid notification type for page followers: {notification_type}")
            return 0
        
        # Get followers from both PageFollow (legacy) and Follow (new generic system)
        from pages.models import PageFollow
        from core.models_follow import Follow
        
        # Legacy PageFollow followers
        legacy_followers = User.objects.filter(
            page_follows__page=page
        ).distinct()
        
        # New generic Follow system followers
        generic_followers = User.objects.filter(
            follows__entity_type='temple',
            follows__entity_id=page.id
        ).distinct()
        
        # Combine both sets (distinct users)
        all_follower_ids = set(legacy_followers.values_list('id', flat=True))
        all_follower_ids.update(generic_followers.values_list('id', flat=True))
        
        followers = User.objects.filter(id__in=all_follower_ids)
        
        count = 0
        for follower in followers:
            notification = NotificationService.create_notification(
                recipient=follower,
                notification_type=notification_type,
                source_module='pages',
                payload=payload,
                page=page,  # Link to temple
            )
            if notification:
                count += 1
        
        logger.info(f"Notified {count} followers of Page {page.id}")
        return count
    
    @staticmethod
    def notify_pandit_followers(
        pandit_profile,
        notification_type: str,
        payload: Dict[str, Any]
    ) -> int:
        """
        Notify all followers of a Pandit.
        
        EXTENDED: Uses generic Follow model for pandit notifications
        
        Args:
            pandit_profile: PanditProfile instance
            notification_type: Type of notification
            payload: Notification payload
            
        Returns:
            int: Number of notifications created
        """
        # Get followers from Follow system
        from core.models_follow import Follow
        
        followers = User.objects.filter(
            follows__entity_type='pandit',
            follows__entity_id=pandit_profile.id
        ).distinct()
        
        count = 0
        for follower in followers:
            notification = NotificationService.create_notification(
                recipient=follower,
                notification_type=notification_type,
                source_module='profiles',
                payload=payload,
            )
            if notification:
                count += 1
        
        logger.info(f"Notified {count} followers of PanditProfile {pandit_profile.id}")
        return count
    
    @staticmethod
    def notify_booking_intent_participants(
        booking_intent,
        notification_type: str,
        payload: Dict[str, Any]
    ) -> int:
        """
        Notify participants in a booking intent.
        
        Task 17.6: Booking Intent Notification Rules
        
        Args:
            booking_intent: BookingIntent instance
            notification_type: Type of notification (must be BOOKING_INTENT)
            payload: Notification payload
            
        Returns:
            int: Number of notifications created
        """
        if notification_type != NOTIFICATION_TYPE_BOOKING_INTENT:
            logger.warning(f"Invalid notification type for booking intent: {notification_type}")
            return 0
        
        count = 0
        
        # Notify Pandit
        if booking_intent.pandit:
            notification = NotificationService.create_notification(
                recipient=booking_intent.pandit,
                notification_type=notification_type,
                source_module='booking_intent',
                payload=payload,
            )
            if notification:
                count += 1
        
        # Notify requester
        if booking_intent.requester:
            notification = NotificationService.create_notification(
                recipient=booking_intent.requester,
                notification_type=notification_type,
                source_module='booking_intent',
                payload=payload,
            )
            if notification:
                count += 1
        
        return count
    
    @staticmethod
    def notify_review_participants(
        review,
        notification_type: str,
        payload: Dict[str, Any]
    ) -> int:
        """
        Notify participants in a review.
        
        Task 17.7: Review & Interaction Notification Rules
        
        Args:
            review: Review instance
            notification_type: Type of notification (must be REVIEW)
            payload: Notification payload
            
        Returns:
            int: Number of notifications created
        """
        if notification_type != NOTIFICATION_TYPE_REVIEW:
            logger.warning(f"Invalid notification type for review: {notification_type}")
            return 0
        
        count = 0
        
        # Notify Pandit (subject of review)
        if review.pandit:
            notification = NotificationService.create_notification(
                recipient=review.pandit,
                notification_type=notification_type,
                source_module='reviews',
                payload=payload,
            )
            if notification:
                count += 1
        
        # Notify admins if review is reported
        if review.is_reported:
            admins = User.objects.filter(role='admin', status='active')
            for admin in admins:
                notification = NotificationService.create_notification(
                    recipient=admin,
                    notification_type=NOTIFICATION_TYPE_GOVERNANCE,
                    source_module='reviews',
                    payload=payload,
                )
                if notification:
                    count += 1
        
        return count
    
    @staticmethod
    def notify_governance_action(
        affected_user: User,
        payload: Dict[str, Any]
    ) -> Optional[Notification]:
        """
        Notify user of a governance action.
        
        Task 17.8: Governance & Moderation Notification Rules
        
        Args:
            affected_user: User affected by governance action
            payload: Notification payload (status-only, no reasoning)
            
        Returns:
            Notification instance or None
        """
        return NotificationService.create_notification(
            recipient=affected_user,
            notification_type=NOTIFICATION_TYPE_GOVERNANCE,
            source_module='governance',
            payload=payload,
        )
    
    @staticmethod
    def send_temple_notification(
        *,
        sender: User,
        page,  # Page instance (Temple)
        title: str,
        message: str
    ) -> int:
        """
        Send temple-scoped notification to all eligible users.
        
        Temple-Scoped Notification System (Safe, Additive, Governance-Compliant)
        
        Rules:
        - Only Pandit, Admin Pandit, Super Admin can send
        - All authenticated users (including End Users) can receive
        - Must be linked to exactly ONE Temple/Page
        - Non-blocking: failures don't break main action
        - Non-authoritative: notifications don't affect business logic
        
        Args:
            sender: User sending the notification (must be Pandit, Admin Pandit, or Super Admin)
            page: Page instance (Temple) this notification is linked to
            title: Notification title
            message: Notification message
            
        Returns:
            int: Number of notifications created
        """
        # VALIDATION: Only Pandit, Admin Pandit, Super Admin can send
        if sender.role not in ['pandit', 'admin'] and not sender.is_superuser:
            logger.warning(f"User {sender.id} ({sender.role}) attempted to send temple notification - denied")
            return 0
        
        # VALIDATION: Page must exist and be active
        if not page or page.status != 'ACTIVE':
            logger.warning(f"Invalid page for temple notification: page={page}, status={getattr(page, 'status', None)}")
            return 0
        
        # VALIDATION: Title and message required
        if not title or not message:
            logger.warning(f"Temple notification missing title or message: title={bool(title)}, message={bool(message)}")
            return 0
        
        # Wrap entire operation in try/except to ensure non-blocking
        try:
            # Recipients: (1) End users and pandits who follow this temple; (2) Admin Pandit + Super Admin always
            from django.contrib.auth import get_user_model
            from django.db.models import Q
            from pages.models import PageFollow
            from core.models_follow import Follow

            User = get_user_model()

            # Followers from PageFollow (legacy) and Follow (generic)
            legacy_follower_ids = set(PageFollow.objects.filter(page=page).values_list('follower_id', flat=True))
            generic_follower_ids = set(Follow.objects.filter(
                entity_type='temple',
                entity_id=page.id
            ).values_list('user_id', flat=True))
            all_follower_ids = legacy_follower_ids | generic_follower_ids

            # End users and pandits: only if they follow
            followers_who_get_notification = User.objects.filter(
                id__in=all_follower_ids,
                is_active=True
            ).filter(Q(role='user') | Q(role='pandit')).values_list('id', flat=True)

            # Admin Pandit and Super Admin: always get temple notifications (with or without follow)
            admin_and_super_ids = set(User.objects.filter(
                Q(role='admin') | Q(is_superuser=True),
                is_active=True
            ).values_list('id', flat=True))

            recipient_ids = set(followers_who_get_notification) | admin_and_super_ids
            recipients = User.objects.filter(id__in=recipient_ids, is_active=True)
            
            # Create notification payload (safe, no PII, no internal IDs)
            # Include temple location for better context
            temple_location = page.address if page.address else ''
            if page.city:
                temple_location = f"{temple_location}, {page.city.name}" if temple_location else page.city.name
            if page.area:
                temple_location = f"{temple_location}, {page.area.name}" if temple_location else page.area.name
            
            payload = {
                'title': title,
                'message': message,
                'temple_name': page.title,  # Public name only
                'temple_location': temple_location,  # Temple address/location
                'temple_public_id': page.public_id,  # Public ID only, not internal ID
            }
            
            count = 0
            for recipient in recipients:
                # Check eligibility (all authenticated users are eligible for temple announcements)
                if NotificationService.is_eligible_for_notification(recipient, NOTIFICATION_TYPE_TEMPLE_ANNOUNCEMENT):
                    # Create notification (non-blocking: failures are logged but don't stop the process)
                    notification = NotificationService.create_notification(
                        recipient=recipient,
                        notification_type=NOTIFICATION_TYPE_TEMPLE_ANNOUNCEMENT,
                        source_module='pages',
                        payload=payload,
                        page=page,  # Link to temple
                    )
                    if notification:
                        count += 1
            
            logger.info(f"Temple notification sent: {count} notifications created for Page {page.id} by {sender.email}")
            return count
            
        except Exception as e:
            # CRITICAL: Never raise exceptions - this is non-blocking
            logger.error(f"Error sending temple notification: {e}", exc_info=True)
            return 0
    
    @staticmethod
    def cleanup_expired_notifications() -> int:
        """
        Clean up expired notifications.
        
        Task 17.10: Notification Visibility, Read State & Expiry
        
        This is a maintenance operation, not a business decision.
        
        Returns:
            int: Number of notifications cleaned up
        """
        expired_count = Notification.objects.filter(
            expires_at__lte=timezone.now()
        ).delete()[0]
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired notifications")
        
        return expired_count

