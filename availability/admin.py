from django.contrib import admin
from .models import Availability


@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    """
    Admin interface for Availability model.
    
    Note: This is a basic admin configuration.
    Full admin customization will be done in future tasks if needed.
    """
    list_display = ('pandit', 'city', 'day_of_week', 'specific_date', 'start_time', 'end_time', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_recurring', 'city', 'pooja', 'created_at')
    search_fields = ('pandit__email', 'pandit__first_name', 'pandit__last_name', 'city__name', 'area__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Ownership', {
            'fields': ('pandit',)
        }),
        ('Temporal Information', {
            'fields': ('day_of_week', 'specific_date', 'start_time', 'end_time', 'is_recurring')
        }),
        ('Context', {
            'fields': ('city', 'area', 'pooja')
        }),
        ('State', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )




































