"""
Engagement models for user behavior capture.

This module provides APPEND-ONLY event logging for future news feed intelligence.
NO analytics, ranking, or sentiment analysis. Raw facts only.

Architecture:
- Dual-ID Strategy: Internal BIGINT (joins) + Public UUIDv7 (exposure)
- Immutable: Events are never updated or deleted
- Future-ready: Can be consumed by feed engine later
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from core.public_id import generate_public_id
from core.audit import log_blocked_deletion
from .constants import (
    INTERACTION_TYPES,
    ENTITY_TYPES,
    COMMENT_STATUS_CHOICES,
    COMMENT_STATUS_ACTIVE,
)


class UserInteractionEvent(models.Model):
    """
    Core event log for user interactions.
    
    APPEND-ONLY: Events are never updated or deleted.
    Used to capture raw user behavior for future feed intelligence.
    
    Security:
    - Uses public_id (UUIDv7) for entity references
    - Never stores PII in metadata
    - Immutable after creation
    """
    
    # Dual-ID Strategy
    id = models.BigAutoField(primary_key=True)  # Internal: for joins/performance
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier. Internal ID (id) is used for database joins.'
    )
    
    # Event Details
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # Delete events if user is deleted
        related_name='interaction_events',
        verbose_name='User',
        help_text='User who performed the interaction'
    )
    
    entity_type = models.CharField(
        max_length=50,
        choices=[(t, t) for t in ENTITY_TYPES],
        verbose_name='Entity Type',
        help_text='Type of entity being interacted with (e.g., TEMPLE_PAGE, PAGE_POST)'
    )
    
    entity_public_id = models.CharField(
        max_length=36,
        db_index=True,
        verbose_name='Entity Public ID',
        help_text='Public ID (UUIDv7) of the entity being interacted with. TASK 26: Entity remains resolvable even if INVISIBLE.'
    )
    
    interaction_type = models.CharField(
        max_length=30,
        choices=[(t, t) for t in INTERACTION_TYPES],
        verbose_name='Interaction Type',
        help_text='Type of interaction (VIEW, CLICK, LIKE, SHARE, etc.)'
    )
    
    metadata = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Metadata',
        help_text='Optional additional data (bounded, no PII). Future: used for feed intelligence.'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when event occurred'
    )
    
    class Meta:
        db_table = 'engagement_user_interaction_events'
        verbose_name = 'User Interaction Event'
        verbose_name_plural = 'User Interaction Events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['entity_type', 'entity_public_id']),
            models.Index(fields=['interaction_type', 'created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.email} - {self.interaction_type} - {self.entity_type} ({self.public_id[:8]}...)"
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        UserInteractionEvents are append-only and must never be deleted.
        """
        log_blocked_deletion(self, actor=None, reason="UserInteractionEvent hard deletion blocked - events are append-only")
        raise ValidationError(
            f"Hard deletion is not allowed for UserInteractionEvent. "
            f"Events are append-only and immutable for audit purposes."
        )
    
    def clean(self):
        """Validate event data."""
        # Ensure metadata doesn't contain PII
        if self.metadata:
            forbidden_keys = ['email', 'phone', 'phone_number', 'whatsapp_number', 'ip_address', 'ip']
            for key in forbidden_keys:
                if key in self.metadata:
                    raise ValidationError(f"Metadata cannot contain PII field: {key}")


class PostComment(models.Model):
    """
    Comments on posts (e.g., Temple Page posts, Page posts).
    
    This is CONTENT, not an event. Events are logged separately in UserInteractionEvent.
    
    Rules:
    - No sentiment analysis
    - No moderation logic (handled in Governance module)
    - Threading supported via parent_comment
    """
    
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
        help_text='Public-facing UUIDv7 identifier. Internal ID (id) is used for database joins.'
    )
    
    # Comment Content
    post_public_id = models.CharField(
        max_length=36,
        db_index=True,
        verbose_name='Post Public ID',
        help_text='Public ID (UUIDv7) of the post being commented on'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_comments',
        verbose_name='User',
        help_text='User who created the comment'
    )
    
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Parent Comment',
        help_text='Parent comment if this is a reply (for threading)'
    )
    
    comment_text = models.TextField(
        max_length=2000,
        verbose_name='Comment Text',
        help_text='Comment content (max 2000 characters)'
    )
    
    status = models.CharField(
        max_length=20,
        choices=COMMENT_STATUS_CHOICES,
        default=COMMENT_STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Comment status (active, hidden, reported). Moderation handled in Governance module.'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when comment was created'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='Timestamp when comment was last updated'
    )
    
    class Meta:
        db_table = 'engagement_post_comments'
        verbose_name = 'Post Comment'
        verbose_name_plural = 'Post Comments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post_public_id', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        preview = self.comment_text[:50] + '...' if len(self.comment_text) > 50 else self.comment_text
        return f"Comment by {self.user.email} on {self.post_public_id[:8]}... - {preview}"


class PostLike(models.Model):
    """
    Fast counter table for post likes.
    
    Used ONLY for quick counts. Each like/unlike MUST also log a UserInteractionEvent.
    
    Rules:
    - Unique constraint prevents duplicate likes
    - Used for performance (fast count queries)
    - Event logging is primary source of truth
    """
    
    id = models.BigAutoField(primary_key=True)
    
    post_public_id = models.CharField(
        max_length=36,
        db_index=True,
        verbose_name='Post Public ID',
        help_text='Public ID (UUIDv7) of the post being liked'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='post_likes',
        verbose_name='User',
        help_text='User who liked the post'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when like was created'
    )
    
    class Meta:
        db_table = 'engagement_post_likes'
        verbose_name = 'Post Like'
        verbose_name_plural = 'Post Likes'
        unique_together = [['post_public_id', 'user']]  # One like per user per post
        indexes = [
            models.Index(fields=['post_public_id', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} liked {self.post_public_id[:8]}..."
