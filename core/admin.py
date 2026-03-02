from django.contrib import admin
from .models_follow import Follow


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    """Admin interface for Follow model."""
    list_display = ('user', 'entity_type', 'entity_id', 'created_at')
    list_filter = ('entity_type', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('public_id', 'created_at')
    date_hierarchy = 'created_at'
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion from admin - use service layer instead."""
        return False
