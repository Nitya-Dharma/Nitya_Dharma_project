"""
Approval history models for preserving Admin Pandit approval records.

TASK 2: Admin Pandit Approval History Preservation

This module ensures that approval history remains immutable even when
the Admin Pandit who approved others is deactivated.
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
        help_text='Public-facing UUIDv7 identifier'
    )
    
    # Approved Pandit (immutable reference)
    approved_pandit = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Never delete approval records
        related_name='approval_records',
        verbose_name='Approved Pandit',
        help_text='The Pandit who was approved'
    )
    
    # Admin Pandit who approved (nullable if Super Admin approved)
    approved_by_admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # If Admin Pandit deleted, set to NULL but preserve display name
        null=True,
        blank=True,
        related_name='approvals_given',
        verbose_name='Approving Admin Pandit',
        help_text='The Admin Pandit who approved this Pandit (nullable if Super Admin approved)'
    )
    
    # Immutable snapshot of Admin Pandit name at approval time
    approved_by_display_name = models.TextField(
        verbose_name='Approved By Display Name',
        help_text='Immutable snapshot of Admin Pandit name at approval time. Preserved even if Admin Pandit is deactivated.'
    )
    
    # Approval timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Approved At',
        help_text='Timestamp when approval was granted'
    )
    
    # Approval custodian (Super Admin who manages approvals after Admin Pandit deactivation)
    approval_custodian = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='custodianship_approvals',
        verbose_name='Approval Custodian',
        help_text='Super Admin who manages this approval after Admin Pandit deactivation'
    )
    
    class Meta:
        verbose_name = 'Approval Record'
        verbose_name_plural = 'Approval Records'
        db_table = 'governance_approval_records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approved_pandit', 'created_at']),
            models.Index(fields=['approved_by_admin', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        # One approval record per Pandit (latest approval)
        constraints = [
            models.UniqueConstraint(
                fields=['approved_pandit'],
                name='unique_latest_approval_per_pandit'
            )
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        
        # If approved_by_admin is set, capture display name
        if self.approved_by_admin and not self.approved_by_display_name:
            self.approved_by_display_name = self._get_admin_display_name(self.approved_by_admin)
        
        super().save(*args, **kwargs)
    
    def _get_admin_display_name(self, admin_user):
        """Get display name for Admin Pandit."""
        if admin_user.username:
            return admin_user.username
        elif admin_user.get_full_name():
            return admin_user.get_full_name()
        else:
            return admin_user.email
    
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
        admin_name = self.approved_by_display_name or 'Super Admin'
        status = " (Inactive)" if self.approved_by_admin and self.approved_by_admin.status == 'deactivated' else ""
        return f"Approval: {self.approved_pandit.email} by {admin_name}{status}"


class ApprovalCustodian(models.Model):
    """
    Tracks custodianship of approval records when Admin Pandit is deactivated.
    
    This model ensures that approval history remains intact while
    assigning management responsibility to a Super Admin.
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
        help_text='Public-facing UUIDv7 identifier'
    )
    
    # Original Admin Pandit (never modified)
    original_admin_pandit = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approval_custodianships',
        verbose_name='Original Admin Pandit',
        help_text='The Admin Pandit who was deactivated (never modified)'
    )
    
    # Super Admin custodian
    custodian = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='managed_approval_custodianships',
        verbose_name='Custodian Super Admin',
        help_text='Super Admin who manages approvals after Admin Pandit deactivation'
    )
    
    # Reason for custodianship
    reason = models.TextField(
        blank=True,
        verbose_name='Reason',
        help_text='Reason for assigning custodianship'
    )
    
    # Timestamp
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Assigned At',
        help_text='When custodianship was assigned'
    )
    
    class Meta:
        verbose_name = 'Approval Custodian'
        verbose_name_plural = 'Approval Custodians'
        db_table = 'governance_approval_custodians'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['original_admin_pandit']),
            models.Index(fields=['custodian']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        admin_name = self.original_admin_pandit.email if self.original_admin_pandit else 'N/A'
        return f"Custodianship for {admin_name} by {self.custodian.email}"









