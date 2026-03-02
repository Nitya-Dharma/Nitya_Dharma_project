"""
Notification Models

Task 17.2: Notification Types Classification
Task 17.10: Notification Visibility, Read State & Expiry
Task 17.11: User Notification Preferences & Opt-out

Core notification data structures.
No business logic, no delivery guarantees, no authority.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from .constants import NOTIFICATION_TYPE_CHOICES

User = get_user_model()


class Notification(models.Model):
    """
    Notification model.
    
    Stores event-driven notification messages.
    Delivery-only, no business logic, no authority.
    
    TASK 10: Preserves actor reference even if actor is deactivated.
    """
    
    # Actor role choices
    ACTOR_ROLE_END_USER = 'END_USER'
    ACTOR_ROLE_PANDIT = 'PANDIT'
    ACTOR_ROLE_ADMIN_PANDIT = 'ADMIN_PANDIT'
    ACTOR_ROLE_SYSTEM = 'SYSTEM'
    
    ACTOR_ROLE_CHOICES = [
        (ACTOR_ROLE_END_USER, 'End User'),
        (ACTOR_ROLE_PANDIT, 'Pandit'),
        (ACTOR_ROLE_ADMIN_PANDIT, 'Admin Pandit'),
        (ACTOR_ROLE_SYSTEM, 'System'),
    ]
    
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text='User receiving this notification'
    )
    
    # TASK 10: Actor who triggered this notification (preserved even if deactivated)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_notifications',
        help_text='User who triggered this notification (null if actor was deactivated)'
    )
    
    # TASK 10: Immutable snapshot of actor name (preserved even if actor is deactivated)
    actor_display_name = models.TextField(
        null=True,
        blank=True,
        verbose_name='Actor Display Name',
        help_text='Immutable snapshot of the actor name at time of notification. Preserved even if actor is deactivated.'
    )
    
    # TASK 10: Actor role at time of notification (preserved for audit)
    actor_role = models.CharField(
        max_length=20,
        choices=ACTOR_ROLE_CHOICES,
        null=True,
        blank=True,
        verbose_name='Actor Role',
        help_text='Role of the actor at time of notification (preserved for audit)'
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        help_text='Type of notification (descriptive only, no priority)'
    )
    
    source_module = models.CharField(
        max_length=50,
        help_text='Module that triggered this notification (e.g., booking_intent, pages)'
    )
    
    # Temple-scoped notification (additive field - temple notifications must be linked to a Page)
    page = models.ForeignKey(
        'pages.Page',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='Temple/Page',
        help_text='Temple/Page this notification is linked to (required for temple-scoped notifications)'
    )
    
    # Payload (JSONField - SAFE, NO PII)
    # Contains minimal, abstract, non-revealing data only
    payload = models.JSONField(
        default=dict,
        help_text='Notification payload (minimal, no PII, no internal IDs)'
    )
    
    # Read state
    is_read = models.BooleanField(
        default=False,
        help_text='Whether notification has been read by recipient'
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when notification was read'
    )
    
    # Expiry (optional)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Optional expiry timestamp (notifications are ephemeral)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['source_module', '-created_at']),
            models.Index(fields=['actor', '-created_at']),  # TASK 10
            models.Index(fields=['page', '-created_at']),  # Temple-scoped notifications
        ]
    
    def _get_actor_display_name(self, actor_user):
        """Get display name for actor."""
        if actor_user.username:
            return actor_user.username
        elif actor_user.get_full_name():
            return actor_user.get_full_name()
        else:
            return actor_user.email
    
    def _get_actor_role_from_user(self, actor_user):
        """Get actor role from user."""
        if not actor_user:
            return self.ACTOR_ROLE_SYSTEM
        
        if actor_user.is_superuser:
            return self.ACTOR_ROLE_SYSTEM
        elif actor_user.role == 'admin':
            return self.ACTOR_ROLE_ADMIN_PANDIT
        elif actor_user.role == 'pandit':
            return self.ACTOR_ROLE_PANDIT
        else:
            return self.ACTOR_ROLE_END_USER
    
    def save(self, *args, **kwargs):
        """
        TASK 10: Capture actor display name and role for immutable attribution.
        """
        # Capture actor display name if not set
        if self.actor and not self.actor_display_name:
            self.actor_display_name = self._get_actor_display_name(self.actor)
        
        # Capture actor role if not set
        if self.actor and not self.actor_role:
            self.actor_role = self._get_actor_role_from_user(self.actor)
        elif not self.actor and not self.actor_role:
            self.actor_role = self.ACTOR_ROLE_SYSTEM
        
        super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        TASK 10: Notifications must never be hard-deleted. They are immutable.
        """
        from core.audit import log_blocked_deletion
        log_blocked_deletion(self, actor=None, reason="Notification hard deletion blocked - notifications are immutable")
        from django.core.exceptions import ValidationError
        raise ValidationError(
            f"Hard deletion is not allowed for Notification. "
            f"Notifications are immutable and must be preserved for audit purposes."
        )
    
    def __str__(self):
        actor_name = self.actor_display_name or (self.actor.email if self.actor else "System")
        return f"Notification {self.id} - {self.notification_type} for {self.recipient.email} (by {actor_name})"


class NotificationPreference(models.Model):
    """
    User notification preferences.
    
    Task 17.11: User Notification Preferences & Opt-out
    
    Allows users to control optional notifications.
    Mandatory notifications (governance, security) cannot be disabled.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        help_text='User owning these preferences'
    )
    
    # Category preferences (boolean flags)
    # True = enabled, False = disabled
    page_updates_enabled = models.BooleanField(
        default=True,
        help_text='Receive Page update notifications'
    )
    review_notifications_enabled = models.BooleanField(
        default=True,
        help_text='Receive review-related notifications'
    )
    booking_intent_enabled = models.BooleanField(
        default=True,
        help_text='Receive booking intent notifications (non-critical)'
    )
    
    # Role-specific notification preferences
    # For Pandits
    pandit_booking_requests_enabled = models.BooleanField(
        default=True,
        help_text='Receive notifications for new booking requests (Pandit only)'
    )
    pandit_profile_updates_enabled = models.BooleanField(
        default=True,
        help_text='Receive notifications for profile approval status (Pandit only)'
    )
    pandit_review_submissions_enabled = models.BooleanField(
        default=True,
        help_text='Receive notifications when reviews are submitted (Pandit only)'
    )
    
    # For Admin Pandits
    admin_pandit_approval_requests_enabled = models.BooleanField(
        default=True,
        help_text='Receive notifications for pending pandit approvals (Admin Pandit only)'
    )
    admin_pandit_profile_approvals_enabled = models.BooleanField(
        default=True,
        help_text='Receive notifications for profile approval requests (Admin Pandit only)'
    )
    admin_pandit_partial_blocks_enabled = models.BooleanField(
        default=True,
        help_text='Receive notifications for partial block actions (Admin Pandit only)'
    )
    admin_pandit_referral_usage_enabled = models.BooleanField(
        default=True,
        help_text='Receive notifications for referral link usage (Admin Pandit only)'
    )
    
    # For Regular Users
    user_booking_updates_enabled = models.BooleanField(
        default=True,
        help_text='Receive notifications for booking intent updates (User only)'
    )
    user_review_reminders_enabled = models.BooleanField(
        default=True,
        help_text='Receive reminders to submit reviews (User only)'
    )
    
    # Channel preferences (future-ready)
    in_app_enabled = models.BooleanField(
        default=True,
        help_text='Receive in-app notifications'
    )
    email_enabled = models.BooleanField(
        default=False,
        help_text='Receive email notifications (future)'
    )
    push_enabled = models.BooleanField(
        default=False,
        help_text='Receive push notifications (future)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.email}"
