"""
Phase 17A: Feed engine admin. Optional: register FeedItemCandidate for inspection.
"""
from django.contrib import admin
from feed_engine.models import FeedItemCandidate


@admin.register(FeedItemCandidate)
class FeedItemCandidateAdmin(admin.ModelAdmin):
    list_display = ("content_type", "content_id", "engagement_score", "popularity_score", "freshness_score", "updated_at")
    list_filter = ("content_type",)
    search_fields = ("content_type",)
    readonly_fields = ("created_at", "updated_at")
