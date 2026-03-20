"""
Admin for ad analytics events and aggregates (read-only friendly).
Does not modify ad serving.
"""

from django.contrib import admin
from .models import AdImpression, AdClick, AdConversionIntent, AdDailyStats, AdPlacementStats, AdLocationStats, AdRevenueEvent


@admin.register(AdImpression)
class AdImpressionAdmin(admin.ModelAdmin):
    list_display = ("id", "ad", "placement_position", "page_type", "viewer_city", "timestamp")
    list_filter = ("placement_position", "page_type", "device_type")
    search_fields = ("ad__name", "viewer_city", "session_id")
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp",)


@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    list_display = ("id", "ad", "placement_position", "viewer_city", "timestamp")
    list_filter = ("placement_position",)
    search_fields = ("ad__name", "viewer_city")
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp",)


@admin.register(AdConversionIntent)
class AdConversionIntentAdmin(admin.ModelAdmin):
    list_display = ("id", "ad", "conversion_type", "user", "pandit_id", "timestamp")
    list_filter = ("conversion_type",)
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp",)


@admin.register(AdDailyStats)
class AdDailyStatsAdmin(admin.ModelAdmin):
    list_display = ("date", "ad", "placement_position", "impressions", "clicks", "ctr", "unique_users")
    list_filter = ("date", "placement_position")
    search_fields = ("ad__name",)
    date_hierarchy = "date"


@admin.register(AdPlacementStats)
class AdPlacementStatsAdmin(admin.ModelAdmin):
    list_display = ("date", "placement_position", "impressions", "clicks", "ctr")
    list_filter = ("date", "placement_position")
    date_hierarchy = "date"


@admin.register(AdLocationStats)
class AdLocationStatsAdmin(admin.ModelAdmin):
    list_display = ("date", "viewer_city", "viewer_state", "impressions", "clicks", "ctr")
    list_filter = ("date", "viewer_state")
    search_fields = ("viewer_city", "viewer_state")
    date_hierarchy = "date"


@admin.register(AdRevenueEvent)
class AdRevenueEventAdmin(admin.ModelAdmin):
    list_display = ("id", "ad", "billing_model", "impressions", "clicks", "revenue_amount", "timestamp")
    list_filter = ("billing_model",)
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp",)
