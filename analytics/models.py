"""
Analytics Models

Task 14.1: Analytics Event Storage
Task 14.2: Analytics Access Logging

Models for storing analytics events and access logs.
Read-only storage, no business logic.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
import json


class AnalyticsEvent(models.Model):
    """
    Analytics Event model.
    
    Stores individual analytics events for aggregation and analysis.
    All events are privacy-safe (no PII).
    
    Task 14.1: Analytics Event Storage
    """
    
    # Event Identity
    event_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='Event Name',
        help_text='Name of the event (e.g., "search.performed", "review.created")'
    )
    
    event_category = models.CharField(
        max_length=20,
        choices=[
            ('user', 'User'),
            ('pandit', 'Pandit'),
            ('admin', 'Admin'),
            ('system', 'System'),
        ],
        db_index=True,
        verbose_name='Event Category',
        help_text='Category of the event'
    )
    
    # Event Data (JSON metadata)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Metadata',
        help_text='Additional event metadata (JSON format, no PII)'
    )
    
    # Timestamps
    timestamp = models.DateTimeField(
        db_index=True,
        default=timezone.now,
        verbose_name='Event Timestamp',
        help_text='Timestamp when the event occurred'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='Timestamp when this record was created'
    )
    
    class Meta:
        verbose_name = 'Analytics Event'
        verbose_name_plural = 'Analytics Events'
        db_table = 'analytics_analyticsevent'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_name', 'timestamp']),
            models.Index(fields=['event_category', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.event_name} ({self.event_category}) - {self.timestamp}"


class AnalyticsAccessLog(models.Model):
    """
    Analytics Access Log model.
    
    Stores audit trail of who accessed analytics data and when.
    Used for compliance and security auditing.
    
    Task 14.2: Analytics Access Logging
    """
    
    # Accessor
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='analytics_access_logs',
        verbose_name='Accessed By',
        help_text='User who accessed analytics data'
    )
    
    # Access Details
    access_type = models.CharField(
        max_length=50,
        verbose_name='Access Type',
        help_text='Type of access (e.g., "api_query", "dashboard_aggregation", "dashboard_summary")'
    )
    
    # Filters Applied (JSON)
    filters_applied = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Filters Applied',
        help_text='Filters or parameters used in the analytics query (JSON format)'
    )
    
    # Timestamp
    accessed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Accessed At',
        help_text='Timestamp when analytics data was accessed'
    )
    
    class Meta:
        verbose_name = 'Analytics Access Log'
        verbose_name_plural = 'Analytics Access Logs'
        db_table = 'analytics_analyticsaccesslog'
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['accessed_by', 'accessed_at']),
            models.Index(fields=['access_type', 'accessed_at']),
        ]
    
    def __str__(self):
        return f"{self.accessed_by.email} - {self.access_type} - {self.accessed_at}"
