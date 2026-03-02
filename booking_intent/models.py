"""
Booking Intent models.

Task 8.9: Booking Intent Model & Persistence
Task 8.12: Governance Hooks & Reporting

Data definition ONLY — no behavior.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from core.public_id import generate_public_id
from core.audit import log_blocked_deletion


class BookingIntent(models.Model):
    """
    Booking Intent model.
    
    Task 8.9: Booking Intent Model & Persistence
    
    Represents a NON-TRANSACTIONAL signal of interest from a user to a Pandit.
    This is NOT a booking, NOT a reservation, NOT a confirmation.
    
    Key Principles:
    - One intent = one record
    - No slot reservation
    - No availability mutation
    - No business logic in model
    - Append-only (immutable audit fields)
    """
    
    # Status choices (Task 8.4 - State Machine)
    STATUS_SUBMITTED = 'submitted'
    STATUS_VIEWED = 'viewed'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CLOSED_SYSTEM = 'closed_system'  # TASK 21: Auto-closed when Pandit is deactivated
    
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_VIEWED, 'Viewed'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_CLOSED_SYSTEM, 'Closed by System'),  # TASK 21
    ]
    
    # Public ID (UUIDv7 for external-facing URLs)
    public_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this booking intent'
    )
    
    # Core Identity
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # TASK 22: Never delete intent records (audit requirement)
        related_name='booking_intents_created',
        verbose_name='Requester',
        help_text='User who created this booking intent (preserved even if user is deactivated)'
    )
    
    pandit = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # TASK 21: Never delete intent records (audit requirement)
        related_name='booking_intents_received',
        verbose_name='Pandit',
        help_text='Pandit this intent is addressed to. NOTE: Role enforcement (role="pandit") is handled at service/permission layer, not at database level.'
    )
    
    # TASK 22: Immutable snapshot of requester name for display when user is deactivated
    requester_display_name = models.TextField(
        null=True,
        blank=True,
        verbose_name='Requester Display Name',
        help_text='Immutable snapshot of requester name at time of creation. Preserved even if user is deactivated.'
    )
    
    # User mobile number for Pandit to contact user
    user_mobile_number = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name='User Mobile Number',
        help_text='Mobile number provided by the user for the Pandit to contact them'
    )
    
    # Intent Context (Declarative Only - Preferences, Not Constraints)
    optional_requested_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Requested Date',
        help_text='Optional preferred date (preference only, not a constraint)'
    )
    
    optional_requested_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Requested Time',
        help_text='Optional preferred time (preference only, not a constraint)'
    )
    
    message = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        validators=[MaxLengthValidator(500)],
        verbose_name='Message',
        help_text='Optional message from requester to Pandit (max 500 characters)'
    )
    
    # Status Lifecycle
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
        verbose_name='Status',
        help_text='Current status of the booking intent'
    )
    
    # Audit Fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='Timestamp when intent was created'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='Timestamp when intent was last updated'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_booking_intents',
        verbose_name='Created By',
        help_text='User who created this booking intent'
    )
    
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_booking_intents',
        verbose_name='Updated By',
        help_text='User who last updated this booking intent'
    )
    
    # Immutable Audit Fields (Task 8.12: Governance Hooks)
    # These fields capture state at creation time for audit purposes
    requester_status_at_creation = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Requester Status at Creation',
        help_text='Snapshot of requester status when intent was created (for audit)'
    )
    
    pandit_status_at_creation = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Pandit Status at Creation',
        help_text='Snapshot of pandit status when intent was created (for audit)'
    )
    
    # Governance Fields (Task 8.12: Governance Hooks & Reporting)
    is_flagged = models.BooleanField(
        default=False,
        verbose_name='Is Flagged',
        help_text='Whether this intent has been flagged for governance review'
    )
    
    flagged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Flagged At',
        help_text='Timestamp when intent was flagged'
    )
    
    flagged_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='Flagged Reason',
        help_text='Reason for flagging (admin-only)'
    )
    
    class Meta:
        verbose_name = 'Booking Intent'
        verbose_name_plural = 'Booking Intents'
        db_table = 'booking_intent_bookingintent'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['pandit', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set and capture requester display name."""
        if not self.public_id:
            self.public_id = generate_public_id()
        
        # TASK 22: Capture requester display name if not set
        if not self.requester_display_name and self.requester:
            self.requester_display_name = self.requester.get_full_name() or self.requester.email
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Intent {self.id}: {self.requester.email} → {self.pandit.email} ({self.status})"
    
    def clean(self):
        """
        Model-level validation.
        
        Note: This is for Django admin/forms only, not runtime enforcement.
        Business logic validation happens in services layer.
        """
        from django.core.exceptions import ValidationError
        
        # Ensure requester and pandit are different
        if self.requester_id and self.pandit_id:
            if self.requester_id == self.pandit_id:
                raise ValidationError('Requester and Pandit must be different users.')
        
        # Ensure pandit has role='pandit' (conceptual check, not enforced at DB level)
        # Actual enforcement happens in services/permissions layer
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        BookingIntents must never be hard-deleted. Use status='cancelled' for cancellation.
        """
        log_blocked_deletion(self, actor=None, reason="BookingIntent hard deletion blocked - use status='cancelled' instead")
        raise ValidationError(
            f"Hard deletion is not allowed for BookingIntent. "
            f"Use status='cancelled' to cancel the intent. "
            f"Intent records are preserved for audit purposes."
        )
