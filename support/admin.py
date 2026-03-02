"""
Admin configuration for Support app.
"""
from django.contrib import admin
from .models import ContactRequest


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'mobile_number', 'subject', 'role_at_submission', 'status', 'created_at')
    list_filter = ('status', 'role_at_submission', 'created_at')
    search_fields = ('email', 'mobile_number', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Contact Information', {
            'fields': ('submitted_by', 'role_at_submission', 'email', 'mobile_number')
        }),
        ('Request Details', {
            'fields': ('subject', 'message', 'selected_reasons')
        }),
        ('Status & Handling', {
            'fields': ('status', 'handled_by', 'admin_reply')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
