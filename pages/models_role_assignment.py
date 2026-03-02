"""
Page role assignment models for tracking Pandit admin/moderator access to Pages.

TASK 3: Pandit Associated with Multiple Temple Pages

This module ensures that page association history is preserved when
Pandits with page admin/moderator roles are deactivated.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.public_id import generate_public_id
from core.audit import log_blocked_deletion

User = get_user_model()


class PageRoleAssignment(models.Model):
    """
    Tracks admin/moderator role assignments for Pandits on Pages.
    
    TASK 3: Preserves association history when Pandit is deactivated.
    
    Rules:
    - Pages must NEVER be deleted
    - Pandit association history must NEVER be removed
    - Content attribution must NEVER be erased
    - Pandit edit rights revoked on deactivation
    - Super Admin becomes temporary custodian
    """
    
    # Role choices
    ROLE_ADMIN = 'ADMIN'
    ROLE_MODERATOR = 'MODERATOR'
    
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MODERATOR, 'Moderator'),
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
        on_delete=models.PROTECT,  # Never delete role assignments
        related_name='role_assignments',
        verbose_name='Page',
        help_text='The Page this role assignment is for'
    )
    
    # Pandit who has the role
    pandit = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Never delete role assignments
        related_name='page_role_assignments',
        verbose_name='Pandit',
        help_text='The Pandit who has this role (must have role="pandit")'
    )
    
    # Role type
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        db_index=True,
        verbose_name='Role',
        help_text='Role type: ADMIN or MODERATOR'
    )
    
    # Who granted this role
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_page_roles',
        verbose_name='Granted By',
        help_text='User who granted this role'
    )
    
    # When role was granted (TASK 5)
    granted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Granted At',
        help_text='Timestamp when role was granted'
    )
    
    # When role was revoked (null = active)
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Revoked At',
        help_text='Timestamp when role was revoked (null = active)'
    )
    
    # Reason for revocation (TASK 5)
    revoked_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name='Revoked Reason',
        help_text='Reason why this role was revoked'
    )
    
    # History preservation flag
    history_preserved = models.BooleanField(
        default=True,
        verbose_name='History Preserved',
        help_text='Flag indicating that this record preserves historical association'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='When this role was assigned'
    )
    
    class Meta:
        verbose_name = 'Page Role Assignment'
        verbose_name_plural = 'Page Role Assignments'
        db_table = 'pages_page_role_assignments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['page', 'pandit']),
            models.Index(fields=['pandit', 'revoked_at']),
            models.Index(fields=['page', 'role', 'revoked_at']),
        ]
        # One active role per Pandit per Page
        constraints = [
            models.UniqueConstraint(
                fields=['page', 'pandit'],
                condition=models.Q(revoked_at__isnull=True),
                name='unique_active_role_per_pandit_per_page'
            )
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set, and set granted_at if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        if not self.granted_at:
            self.granted_at = timezone.now()
        super().save(*args, **kwargs)
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        Role assignment records must never be deleted to preserve history.
        """
        log_blocked_deletion(self, actor=None, reason="PageRoleAssignment hard deletion blocked - history must be preserved")
        raise ValidationError(
            f"Hard deletion is not allowed for PageRoleAssignment. "
            f"Role assignment records must be preserved for audit purposes. Use revoke() instead."
        )
    
    def revoke(self, reason=None, actor=None):
        """
        Revoke this role assignment (soft revocation).
        
        TASK 5: Preserves edit history and attribution while revoking permissions.
        
        Args:
            reason (str, optional): Reason for revocation
            actor (User, optional): User performing revocation
        
        Returns:
            bool: True if revocation was successful
        """
        if self.revoked_at:
            return True  # Already revoked
        
        self.revoked_at = timezone.now()
        self.revoked_reason = reason or "Role revoked"
        self.save(update_fields=['revoked_at', 'revoked_reason'])
        
        # Log audit event
        from core.audit import log_deactivation
        log_deactivation(
            self,
            actor=actor,
            reason=reason or "Role revoked - permissions removed, history preserved"
        )
        
        return True
    
    def is_active(self):
        """Check if this role assignment is currently active."""
        return self.revoked_at is None
    
    def __str__(self):
        status = "Active" if self.is_active() else f"Revoked at {self.revoked_at}"
        return f"{self.pandit.email} - {self.role} on {self.page.title} ({status})"


class PageCustodian(models.Model):
    """
    Tracks custodianship of Pages when Pandit creator/admin is deactivated.
    
    This model ensures that page management continues under Super Admin
    while preserving original creator/admin attribution.
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
    
    # Page reference
    page = models.ForeignKey(
        'pages.Page',
        on_delete=models.PROTECT,
        related_name='custodianship_records',
        verbose_name='Page',
        help_text='The Page under custodianship'
    )
    
    # Original Pandit (never modified)
    original_pandit = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='page_custodianships',
        verbose_name='Original Pandit',
        help_text='The Pandit who was deactivated (never modified)'
    )
    
    # Super Admin custodian
    custodian = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='managed_page_custodianships',
        verbose_name='Custodian Super Admin',
        help_text='Super Admin who manages this page after Pandit deactivation'
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
        verbose_name = 'Page Custodian'
        verbose_name_plural = 'Page Custodians'
        db_table = 'pages_page_custodians'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['page']),
            models.Index(fields=['original_pandit']),
            models.Index(fields=['custodian']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        pandit_name = self.original_pandit.email if self.original_pandit else 'N/A'
        return f"Custodianship for {self.page.title} (original: {pandit_name}) by {self.custodian.email}"
