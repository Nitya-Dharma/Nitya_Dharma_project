from django.contrib import admin
from .models import BehaviorEvent, UserBehaviorEvent


@admin.register(BehaviorEvent)
class BehaviorEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "entity_type", "entity_id", "user", "created_at")
    list_filter = ("event_type", "entity_type", "created_at")
    search_fields = ("event_type", "entity_id", "session_id")
    readonly_fields = (
        "user", "session_id", "event_type", "entity_type", "entity_id",
        "page_url", "page_title", "referrer", "device_type", "browser",
        "os", "screen_resolution", "metadata", "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False  # Events are created only via tracking endpoint

    def has_delete_permission(self, request, obj=None):
        return False  # Behavior data is append-only; never manually deleted


@admin.register(UserBehaviorEvent)
class UserBehaviorEventAdmin(admin.ModelAdmin):
    """Phase 14: Server-side behavior analytics events (search, profile, booking, reviews, page views)."""
    list_display = ("event_type", "object_type", "object_id", "user", "created_at")
    list_filter = ("event_type", "object_type", "created_at")
    search_fields = ("event_type", "session_id")
    readonly_fields = (
        "event_type", "user", "session_id", "object_type", "object_id",
        "metadata", "ip_address", "user_agent", "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False  # Events created only via tracking

    def has_delete_permission(self, request, obj=None):
        return False  # Append-only
