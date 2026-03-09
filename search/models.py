"""
Search Models

TASK 20: Saved Searches with Removed Entities
Phase 11C1: Search Result Click Tracking
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


class SearchQueryLog(models.Model):
    """
    Phase 10E: Aggregated search query analytics for trending searches.
    One row per normalized query; search_count and last_searched_at updated on each search.
    """
    query = models.CharField(max_length=100, db_index=True)
    normalized_query = models.CharField(max_length=100, unique=True, db_index=True)
    search_count = models.PositiveIntegerField(default=1)
    last_searched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'search_searchquerylog'
        verbose_name = 'Search Query Log'
        verbose_name_plural = 'Search Query Logs'
        ordering = ['-search_count']
        indexes = [
            models.Index(fields=['normalized_query'], name='search_sql_norm_idx'),
            models.Index(fields=['-search_count'], name='search_sql_count_idx'),
        ]

    def __str__(self):
        return f"{self.normalized_query} ({self.search_count})"


class RelatedSearchLog(models.Model):
    """
    Phase 10F: Related search pairs for "People also searched for".
    One row per (source_query, related_query); pair_count and last_seen updated on each sequence.
    """
    source_query = models.CharField(max_length=100, db_index=True)
    related_query = models.CharField(max_length=100, db_index=True)
    pair_count = models.PositiveIntegerField(default=1)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "search_relatedsearchlog"
        verbose_name = "Related Search Log"
        verbose_name_plural = "Related Search Logs"
        ordering = ["-pair_count"]
        indexes = [
            models.Index(fields=["source_query"], name="search_rsl_source_idx"),
            models.Index(fields=["related_query"], name="search_rsl_related_idx"),
            models.Index(fields=["-pair_count"], name="search_rsl_count_idx"),
        ]

    def __str__(self):
        return f"{self.source_query} → {self.related_query} ({self.pair_count})"


class SearchResultClick(models.Model):
    """
    Phase 11C1: Tracks which pandit profiles users click from search results.
    Used for popularity analytics, ranking improvements, and trending pandits.
    """
    query = models.CharField(max_length=100, db_index=True)
    pandit = models.ForeignKey(
        "profiles.PanditProfile",
        on_delete=models.CASCADE,
        related_name="search_result_clicks",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="search_result_clicks",
    )
    session_id = models.CharField(max_length=64, db_index=True)
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_result_click"
        verbose_name = "Search Result Click"
        verbose_name_plural = "Search Result Clicks"
        indexes = [
            models.Index(fields=["query"]),
            models.Index(fields=["pandit"]),
            models.Index(fields=["clicked_at"]),
        ]

    def __str__(self):
        return f"{self.query} → pandit {self.pandit_id} @ {self.clicked_at}"
