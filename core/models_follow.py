"""
Follow System Models

Generic follow model supporting both Pandits and Temple Pages.
Isolated model - no changes to existing models.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from core.public_id import generate_public_id
# Note: Not using DeletionGuardMixin for Follow - users should be able to unfollow
# Cascade protection is handled at ForeignKey level (user FK uses CASCADE, entity uses no FK)


class Follow(models.Model):
    """
    Generic follow model for tracking user follows of entities.
    
    Supports:
    - Pandits (entity_type='pandit', entity_id=pandit_profile_id)
    - Temple Pages (entity_type='temple', entity_id=page_id)
    
    Rules:
    - One follow per user per entity (enforced by unique_together)
    - Silent fail if duplicate (handled in service layer)
    - No cascade deletes affecting existing data
    """
    
    ENTITY_TYPE_CHOICES = [
        ('pandit', 'Pandit'),
        ('temple', 'Temple'),
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
    
    # Follower (End User only)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follows',
        verbose_name='Follower',
        help_text='End User following the entity'
    )
    
    # Entity being followed
    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPE_CHOICES,
        db_index=True,
        verbose_name='Entity Type',
        help_text='Type of entity being followed (pandit or temple)'
    )
    
    entity_id = models.BigIntegerField(
        db_index=True,
        verbose_name='Entity ID',
        help_text='ID of the entity being followed (PanditProfile.id or Page.id)'
    )
    
    # Timestamp
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Created At',
        help_text='Timestamp when user started following the entity'
    )
    
    class Meta:
        verbose_name = 'Follow'
        verbose_name_plural = 'Follows'
        db_table = 'core_follow'
        ordering = ['-created_at']
        unique_together = [['user', 'entity_type', 'entity_id']]  # One follow per user per entity
        indexes = [
            models.Index(fields=['user', 'entity_type', 'entity_id']),
            models.Index(fields=['entity_type', 'entity_id', 'created_at']),
            models.Index(fields=['entity_type', 'entity_id']),  # For follower count queries
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if not set."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.email} follows {self.entity_type} #{self.entity_id}"
    
    # Note: No delete() override needed
    # Users can unfollow by deleting Follow records
    # No cascade deletes from entity side (entity_id is BigInteger, not FK)
    # User deletion will cascade delete follows (via user FK CASCADE)

