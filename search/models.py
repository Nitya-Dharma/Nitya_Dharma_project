"""
Search Models

TASK 20: Saved Searches with Removed Entities

Models for storing saved searches and ensuring resilience to removed entities.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from core.public_id import generate_public_id


class SavedSearch(models.Model):
    """
    Saved Search model.
    
    TASK 20: Saved Searches with Removed Entities
    
    Stores user's saved search filters for later use.
    Filters are validated before execution to ensure resilience.
    """
    
    # Core Identity
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_searches',
        verbose_name='User',
        help_text='User who saved this search'
    )
    
    # Search Name
    name = models.CharField(
        max_length=200,
        verbose_name='Search Name',
        help_text='User-friendly name for this saved search'
    )
    
    # Search Filters (JSON storage for flexibility)
    filters = models.JSONField(
        default=dict,
        verbose_name='Search Filters',
        help_text='JSON object containing search filters (city_id, area_id, pooja_id, page_type, etc.)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='Timestamp when search was saved'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='Timestamp when search was last updated'
    )
    
    # Last executed timestamp
    last_executed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Executed At',
        help_text='Timestamp when search was last executed'
    )
    
    class Meta:
        verbose_name = 'Saved Search'
        verbose_name_plural = 'Saved Searches'
        db_table = 'search_savedsearch'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Saved Search: {self.name} (User: {self.user.email})"
    
    def clean(self):
        """Validate filters structure."""
        if not isinstance(self.filters, dict):
            raise ValidationError('Filters must be a JSON object')
