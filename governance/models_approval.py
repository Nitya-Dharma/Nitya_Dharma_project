"""
Approval history models for preserving Admin Pandit approval records.

TASK 2: Admin Pandit Approval History Preservation

This module ensures that approval history is never lost when Admin Pandits
are deactivated. Approval records are immutable and preserve the historical
truth of who approved which Pandits.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.public_id import generate_public_id
from core.audit import log_blocked_deletion

User = get_user_model()


class ApprovalRecord(models.Model):
    """
    Immutable record of Pandit approval by Admin Pandit.
    
    TASK 2: Preserves approval history when Admin Pandit is deactivated.
    
    Rules:
    - Approval records are NEVER rewritten
    - Approval actor is NEVER reassigned
    - Approved Pandits remain approved
    - Deactivated Admin Pandit remains visible as "Inactive"
    """
    
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
        help_text='Public-facing UUIDv7 identifier for this approval record.'
    )
    
    # Approved Pandit (the one who was approved)
    approved_pandit = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Never delete approval records
        related_name='approval_records',
        verbose_name='Approved Pandit',
        help_text='The Pandit who was approved. This relationship is immutable.'
    )
    
    # Admin Pandit who approved (nullable if admin is deleted)
    approved_by_admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # If admin is deleted, set to NULL but preserve record
        related_name='approvals_given',
        null=True,
        blank=True,
        verbose_name='Approving Admin Pandit',
        help_text='The Admin Pandit who approved this Pandit. Nullable if admin is deactivated.'
    )
    
    # Immutable snapshot of admin name (preserved even if admin is deactivated)
    approved_by_display_name = models.TextField(
        verbose_name='Approving Admin Display Name',
        help_text='Immutable snapshot of the Admin Pandit name at time of approval. Preserved even if admin is deactivated.'
    )
    
    # Approval Custodian (Super Admin who manages approvals after admin deactivation)
    approval_custodian = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='custodial_approvals',
        null=True,
        blank=True,
        verbose_name='Approval Custodian',
        help_text='Super Admin who manages this approval after the original Admin Pandit is deactivated.'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='When this approval was granted.'
    )
    
    # Status
    STATUS_ACTIVE = 'active'
    STATUS_UNDER_CUSTODIANSHIP = 'under_custodianship'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_UNDER_CUSTODIANSHIP, 'Under Custodianship'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Approval status. Changes to UNDER_CUSTODIANSHIP when admin is deactivated.'
    )
    
    class Meta:
        verbose_name = 'Approval Record'
        verbose_name_plural = 'Approval Records'
        db_table = 'governance_approval_record'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approved_pandit', 'status']),
            models.Index(fields=['approved_by_admin', 'status']),
            models.Index(fields=['approval_custodian', 'status']),
        ]
        # One active approval per Pandit
        constraints = [
            models.UniqueConstraint(
                fields=['approved_pandit'],
                condition=models.Q(status='active'),
                name='unique_active_approval_per_pandit'
            )
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        Approval records are immutable and must never be deleted.
        """
        log_blocked_deletion(self, actor=None, reason="ApprovalRecord hard deletion blocked - records are immutable")
        raise ValidationError(
            f"Hard deletion is not allowed for ApprovalRecord. "
            f"Approval records are immutable and must be preserved for audit purposes."
        )
    
    def __str__(self):
        admin_name = self.approved_by_display_name or (self.approved_by_admin.email if self.approved_by_admin else 'Unknown')
        pandit_name = self.approved_pandit.email
        status_label = " (Inactive – Platform Managed)" if self.status == self.STATUS_UNDER_CUSTODIANSHIP else ""
        return f"Approved {pandit_name} by {admin_name}{status_label}"


class ApprovalCustodian(models.Model):
    """
    Tracks custodianship of approval records when Admin Pandit is deactivated.
    
    This model ensures that approval history is preserved and managed by
    Super Admin when the original approving Admin Pandit is deactivated.
    """
    
    id = models.BigAutoField(primary_key=True)
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for this custodianship record.'
    )
    
    # Original Admin Pandit who approved others (now deactivated)
    original_admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='approval_custodianship_records',
        null=True,
        blank=True,
        verbose_name='Original Admin Pandit',
        help_text='The Admin Pandit who originally approved others, now deactivated.'
    )
    
    # Super Admin custodian
    custodian = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='managed_approval_chains',
        verbose_name='Custodian Super Admin',
        help_text='The Super Admin who now manages the approval records of the deactivated Admin Pandit.'
    )
    
    # Reason for custodianship
    reason = models.TextField(
        blank=True,
        verbose_name='Reason for Custodianship',
        help_text='Reason for assigning custodianship (e.g., original admin deactivated).'
    )
    
    # Timestamps
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Assigned At',
        help_text='Timestamp when custodianship was assigned.'
    )
    
    class Meta:
        verbose_name = 'Approval Custodian'
        verbose_name_plural = 'Approval Custodians'
        db_table = 'governance_approval_custodian'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['original_admin']),
            models.Index(fields=['custodian']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        admin_email = self.original_admin.email if self.original_admin else 'N/A'
        return f"Approval custodianship for {admin_email} by {self.custodian.email}"

