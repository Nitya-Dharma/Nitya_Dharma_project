from django.contrib import admin
from .models import BehaviorEvent


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
