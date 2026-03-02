"""
Audit Log Model for tracking all system actions.

TASK 28: Audit Logs Referencing Removed Actors

This module provides an immutable audit log that:
- Preserves actor references even when actors are deactivated
- Stores immutable snapshots of actor identity
- Never allows deletion or modification
- Ensures full audit continuity
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from core.public_id import generate_public_id
from core.audit import log_blocked_deletion


class AuditLog(models.Model):
    """
    Immutable audit log for tracking all system actions.
    
    TASK 28: Audit Logs Referencing Removed Actors
    
    This model stores:
    - Actor information (with immutable snapshot)
    - Action type
    - Target entity
    - Timestamp (immutable)
    
    Rules:
    - Never deleted
    - Never modified
    - Actor references preserved even if actor is deactivated
    """
    
    # Action types
    ACTION_TYPE_CREATE = 'CREATE'
    ACTION_TYPE_UPDATE = 'UPDATE'
    ACTION_TYPE_DELETE = 'DELETE'
    ACTION_TYPE_DEACTIVATE = 'DEACTIVATE'
    ACTION_TYPE_REACTIVATE = 'REACTIVATE'
    ACTION_TYPE_APPROVE = 'APPROVE'
    ACTION_TYPE_REJECT = 'REJECT'
    ACTION_TYPE_LOGIN = 'LOGIN'
    ACTION_TYPE_LOGOUT = 'LOGOUT'
    ACTION_TYPE_OTHER = 'OTHER'
    
    ACTION_TYPE_CHOICES = [
        (ACTION_TYPE_CREATE, 'Create'),
        (ACTION_TYPE_UPDATE, 'Update'),
        (ACTION_TYPE_DELETE, 'Delete'),
        (ACTION_TYPE_DEACTIVATE, 'Deactivate'),
        (ACTION_TYPE_REACTIVATE, 'Reactivate'),
        (ACTION_TYPE_APPROVE, 'Approve'),
        (ACTION_TYPE_REJECT, 'Reject'),
        (ACTION_TYPE_LOGIN, 'Login'),
        (ACTION_TYPE_LOGOUT, 'Logout'),
        (ACTION_TYPE_OTHER, 'Other'),
    ]
    
    # Dual-ID Strategy
    id = models.BigAutoField(primary_key=True)
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier'
    )
    
    # Actor information (TASK 28: Preserved even if actor is deactivated)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # Never delete audit logs when actor is deleted
        related_name='audit_logs',
        null=True,
        blank=True,
        verbose_name='Actor',
        help_text='User who performed the action (preserved even if deactivated)'
    )
    
    actor_public_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Actor Public ID',
        help_text='Public ID (UUIDv7) of the actor'
    )
    
    # TASK 28: Immutable snapshot of actor identity
    actor_display_name = models.TextField(
        null=True,
        blank=True,
        verbose_name='Actor Display Name',
        help_text='Immutable snapshot of actor name at time of action. Preserved even if actor is deactivated.'
    )
    
    actor_role = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Actor Role',
        help_text='Role of the actor at time of action (preserved for audit)'
    )
    
    # Action details
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPE_CHOICES,
        db_index=True,
        verbose_name='Action Type',
        help_text='Type of action performed'
    )
    
    target_entity_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Target Entity Type',
        help_text='Type of entity that was acted upon (e.g., User, Page, Post)'
    )
    
    target_entity_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Target Entity ID',
        help_text='ID of the entity that was acted upon'
    )
    
    target_entity_public_id = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Target Entity Public ID',
        help_text='Public ID (UUIDv7) of the entity that was acted upon'
    )
    
    # Additional metadata
    metadata = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Metadata',
        help_text='Additional action metadata (JSON format)'
    )
    
    # Timestamp (immutable)
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when action occurred (immutable)'
    )
    
    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        db_table = 'core_audit_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['actor', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['target_entity_type', 'target_entity_id']),
            models.Index(fields=['created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id and capture actor snapshot."""
        if not self.public_id:
            self.public_id = generate_public_id()
        
        # TASK 28: Capture actor snapshot if not set
        if self.actor and not self.actor_display_name:
            self.actor_display_name = self.actor.get_full_name() or self.actor.email
        
        if self.actor and not self.actor_public_id:
            # Try to get public_id from actor (if available)
            if hasattr(self.actor, 'public_id') and self.actor.public_id:
                self.actor_public_id = self.actor.public_id
        
        if self.actor and not self.actor_role:
            self.actor_role = self.actor.role if hasattr(self.actor, 'role') else None
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        actor_name = self.actor_display_name or (self.actor.email if self.actor else 'System')
        return f"{self.action_type} by {actor_name} on {self.target_entity_type} ({self.created_at})"
    
    def delete(self, using=None, keep_parents=False):
        """
        TASK 28: Override delete() to prevent hard deletion.
        
        Audit logs are immutable and must never be deleted.
        """
        log_blocked_deletion(
            self,
            actor=None,
            reason="AuditLog hard deletion blocked - audit logs are immutable"
        )
        raise ValidationError(
            f"Hard deletion is not allowed for AuditLog. "
            f"Audit logs are immutable and must be preserved for compliance and security purposes."
        )


def create_audit_log(
    action_type: str,
    actor=None,
    target_entity_type: str = None,
    target_entity_id: int = None,
    target_entity_public_id: str = None,
    metadata: dict = None
) -> AuditLog:
    """
    TASK 28: Create an audit log entry.
    
    Args:
        action_type: Type of action (from AuditLog.ACTION_TYPE_CHOICES)
        actor: User who performed the action (optional)
        target_entity_type: Type of entity acted upon (optional)
        target_entity_id: ID of entity acted upon (optional)
        target_entity_public_id: Public ID of entity acted upon (optional)
        metadata: Additional metadata (optional)
    
    Returns:
        AuditLog: Created audit log instance
    """
    return AuditLog.objects.create(
        action_type=action_type,
        actor=actor,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        target_entity_public_id=target_entity_public_id,
        metadata=metadata or {}
    )







