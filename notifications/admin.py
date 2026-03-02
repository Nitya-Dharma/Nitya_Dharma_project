"""
Django Admin for Notifications

Admin interface for viewing notifications (read-only for most users).
"""

from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification model.
    
    Read-only for most fields to preserve audit integrity.
    """
    list_display = [
        'id',
        'recipient',
        'notification_type',
        'source_module',
        'is_read',
        'created_at',
    ]
    list_filter = [
        'notification_type',
        'source_module',
        'is_read',
        'created_at',
    ]
    search_fields = [
        'recipient__email',
        'notification_type',
        'source_module',
    ]
    readonly_fields = [
        'id',
        'recipient',
        'notification_type',
        'source_module',
        'payload',
        'created_at',
        'read_at',
    ]
    ordering = ['-created_at']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """
    Admin interface for NotificationPreference model.
    """
    list_display = [
        'user',
        'page_updates_enabled',
        'review_notifications_enabled',
        'booking_intent_enabled',
        'in_app_enabled',
        'email_enabled',
        'push_enabled',
        'updated_at',
    ]
    list_filter = [
        'page_updates_enabled',
        'review_notifications_enabled',
        'booking_intent_enabled',
        'in_app_enabled',
        'email_enabled',
        'push_enabled',
    ]
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'updated_at']
