"""
Page access request models for tracking Pandit requests to manage Temple Pages.

TASK 13: Pandit Access Requests When Admin Pandit Is Removed

This module ensures that:
- Access requests are never lost
- Requests are rerouted to Super Admin when Admin Pandit is removed
- Original request metadata is preserved
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.public_id import generate_public_id
from core.audit import log_blocked_deletion

User = get_user_model()


class PageAccessRequest(models.Model):
    """
    Tracks Pandit requests for access to manage Temple Pages.
    
    TASK 13: Preserves requests when Admin Pandit reviewer is removed.
    
    Rules:
    - Requests must NEVER disappear
    - Requests must NOT auto-reject
    - Requests rerouted to Super Admin when Admin Pandit is removed
    - Original metadata preserved
    """
    
    # Status choices
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]
    
    # Dual-ID Strategy
    id = models.BigAutoField(primary_key=True)
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier'
    )
    
    # Page reference
    page = models.ForeignKey(
        'pages.Page',
        on_delete=models.PROTECT,  # Never delete access requests
        related_name='access_requests',
        verbose_name='Page',
        help_text='The Page access is requested for'
    )
    
    # Pandit requesting access
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Never delete access requests
        related_name='page_access_requests',
        verbose_name='Requested By',
        help_text='Pandit requesting access (must have role="pandit")'
    )
    
    # TASK 13: Admin Pandit who was originally responsible (can be null if reassigned)
    requested_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_page_access_requests',
        verbose_name='Requested To',
        help_text='Admin Pandit originally responsible for this request (null if reassigned to Super Admin)'
    )
    
    # Request status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name='Status',
        help_text='Request status (PENDING, APPROVED, REJECTED)'
    )
    
    # Request message (optional)
    message = models.TextField(
        blank=True,
        verbose_name='Message',
        help_text='Optional message from requester'
    )
    
    # Resolution details
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_page_access_requests',
        verbose_name='Resolved By',
        help_text='User who approved/rejected this request'
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Resolved At',
        help_text='Timestamp when request was resolved'
    )
    
    resolution_reason = models.TextField(
        blank=True,
        verbose_name='Resolution Reason',
        help_text='Reason for approval/rejection'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='When this request was created'
    )
    
    class Meta:
        verbose_name = 'Page Access Request'
        verbose_name_plural = 'Page Access Requests'
        db_table = 'pages_page_access_request'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['page', 'status']),
            models.Index(fields=['requested_by', 'status']),
            models.Index(fields=['requested_to', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        TASK 13: Access requests must never be deleted.
        """
        log_blocked_deletion(self, actor=None, reason="PageAccessRequest hard deletion blocked - requests must be preserved")
        raise ValidationError(
            f"Hard deletion is not allowed for PageAccessRequest. "
            f"Access requests must be preserved for audit purposes."
        )
    
    def approve(self, approved_by, reason=None):
        """
        Approve this access request.
        
        Args:
            approved_by: User instance (must be Super Admin or original requested_to)
            reason (str, optional): Reason for approval
        """
        if self.status != self.STATUS_PENDING:
            raise ValidationError(f"Request {self.id} is not pending.")
        
        self.status = self.STATUS_APPROVED
        self.resolved_by = approved_by
        self.resolved_at = timezone.now()
        self.resolution_reason = reason or "Access request approved"
        self.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_reason'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=approved_by,
            reason=f"PAGE_ACCESS_REQUEST_APPROVED - Request ID: {self.id}"
        )
    
    def reject(self, rejected_by, reason=None):
        """
        Reject this access request.
        
        Args:
            rejected_by: User instance (must be Super Admin or original requested_to)
            reason (str, optional): Reason for rejection
        """
        if self.status != self.STATUS_PENDING:
            raise ValidationError(f"Request {self.id} is not pending.")
        
        if not reason:
            raise ValidationError("Rejection reason is required.")
        
        self.status = self.STATUS_REJECTED
        self.resolved_by = rejected_by
        self.resolved_at = timezone.now()
        self.resolution_reason = reason
        self.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_reason'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=rejected_by,
            reason=f"PAGE_ACCESS_REQUEST_REJECTED - Request ID: {self.id}, Reason: {reason}"
        )
    
    def __str__(self):
        return f"Access request by {self.requested_by.email} for {self.page.title} ({self.status})"







