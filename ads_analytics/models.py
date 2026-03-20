"""
Advertisement analytics event and aggregation models.

Append-only event tables for impressions and clicks; aggregated daily stats
for dashboard and KPI queries. Does not modify ad placement or serving.
"""

from django.db import models
from django.conf import settings


# Max lengths for location / referrer (avoid unbounded text)
LOCATION_MAX_LENGTH = 150
REFERRER_MAX_LENGTH = 500
PAGE_URL_MAX_LENGTH = 2048
PAGE_TYPE_MAX_LENGTH = 50
PLACEMENT_MAX_LENGTH = 50
DEVICE_MAX_LENGTH = 20


class AdImpression(models.Model):
    """
    One record per advertisement display (append-only).
    Supports WHERE, WHAT, WHEN, WHO, WHY, HOW analytics per docs/advertisement_analytics_detailed_kpis.md.
    """
    ad = models.ForeignKey(
        "ads.Advertisement",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="analytics_impressions",
    )
    campaign_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    placement_position = models.CharField(max_length=PLACEMENT_MAX_LENGTH, db_index=True)
    page_type = models.CharField(max_length=PAGE_TYPE_MAX_LENGTH, blank=True, db_index=True)
    page_url = models.CharField(max_length=PAGE_URL_MAX_LENGTH, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="ad_impressions",
    )
    pandit_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=40, blank=True, db_index=True)
    device_type = models.CharField(max_length=DEVICE_MAX_LENGTH, blank=True, db_index=True)
    viewer_city = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True, db_index=True)
    viewer_area = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True)
    viewer_state = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True, db_index=True)
    viewer_country = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True, db_index=True)
    referrer_source = models.CharField(max_length=REFERRER_MAX_LENGTH, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "ads_analytics"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["ad", "timestamp"]),
            models.Index(fields=["placement_position", "timestamp"]),
            models.Index(fields=["viewer_city", "timestamp"]),
            models.Index(fields=["pandit_id", "timestamp"]),
        ]


class AdClick(models.Model):
    """
    One record per ad click (append-only).
    """
    ad = models.ForeignKey(
        "ads.Advertisement",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="analytics_clicks",
    )
    campaign_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    placement_position = models.CharField(max_length=PLACEMENT_MAX_LENGTH, db_index=True)
    page_type = models.CharField(max_length=PAGE_TYPE_MAX_LENGTH, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="ad_clicks",
    )
    pandit_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=40, blank=True, db_index=True)
    viewer_city = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True, db_index=True)
    viewer_area = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True)
    viewer_state = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True)
    viewer_country = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True)
    referrer_source = models.CharField(max_length=REFERRER_MAX_LENGTH, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "ads_analytics"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["ad", "timestamp"]),
            models.Index(fields=["placement_position", "timestamp"]),
            models.Index(fields=["viewer_city", "timestamp"]),
            models.Index(fields=["pandit_id", "timestamp"]),
        ]


class AdConversionIntent(models.Model):
    """
    Optional: conversion intent events (e.g. booking_intent after ad click).
    Supports conversion attribution per detailed KPIs doc.
    """
    CONVERSION_BOOKING_INTENT = "booking_intent"
    CONVERSION_PROFILE_VIEW = "profile_view"
    CONVERSION_OTHER = "other"
    CONVERSION_TYPES = [
        (CONVERSION_BOOKING_INTENT, "Booking intent"),
        (CONVERSION_PROFILE_VIEW, "Profile view"),
        (CONVERSION_OTHER, "Other"),
    ]

    ad = models.ForeignKey(
        "ads.Advertisement",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="analytics_conversions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        related_name="ad_conversion_intents",
    )
    pandit_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    conversion_type = models.CharField(max_length=50, choices=CONVERSION_TYPES, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "ads_analytics"
        ordering = ["-timestamp"]


# --- Aggregated models (Phase 3) ---


class AdDailyStats(models.Model):
    """
    Daily aggregates per ad (and optionally per placement/location).
    Populated by aggregate_daily_ad_metrics.
    Null/blank placement_position, viewer_city, viewer_state = totals for that ad/date.
    """
    date = models.DateField(db_index=True)
    ad = models.ForeignKey(
        "ads.Advertisement",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="daily_stats",
    )
    placement_position = models.CharField(max_length=PLACEMENT_MAX_LENGTH, null=True, blank=True, db_index=True)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)
    viewer_city = models.CharField(max_length=LOCATION_MAX_LENGTH, null=True, blank=True)
    viewer_state = models.CharField(max_length=LOCATION_MAX_LENGTH, null=True, blank=True)

    class Meta:
        app_label = "ads_analytics"
        ordering = ["-date", "ad"]
        unique_together = [["date", "ad", "placement_position", "viewer_city", "viewer_state"]]
        indexes = [
            models.Index(fields=["date", "ad"]),
            models.Index(fields=["date", "placement_position"]),
        ]

    @property
    def ctr(self):
        if self.impressions == 0:
            return 0.0
        return round(100.0 * self.clicks / self.impressions, 2)


class AdPlacementStats(models.Model):
    """Daily aggregates per placement (platform-level)."""
    date = models.DateField(db_index=True)
    placement_position = models.CharField(max_length=PLACEMENT_MAX_LENGTH, db_index=True)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "ads_analytics"
        ordering = ["-date", "placement_position"]
        unique_together = [["date", "placement_position"]]

    @property
    def ctr(self):
        if self.impressions == 0:
            return 0.0
        return round(100.0 * self.clicks / self.impressions, 2)


class AdLocationStats(models.Model):
    """Daily aggregates per location (city/state)."""
    date = models.DateField(db_index=True)
    viewer_city = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True, db_index=True)
    viewer_state = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True, db_index=True)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "ads_analytics"
        ordering = ["-date", "viewer_city", "viewer_state"]
        unique_together = [["date", "viewer_city", "viewer_state"]]

    @property
    def ctr(self):
        if self.impressions == 0:
            return 0.0
        return round(100.0 * self.clicks / self.impressions, 2)


# --- Revenue (Phase 5) ---

class AdRevenueEvent(models.Model):
    """
    Optional revenue events for CPM/CPC/Sponsored/Featured billing.
    """
    BILLING_CPM = "CPM"
    BILLING_CPC = "CPC"
    BILLING_SPONSORED = "Sponsored"
    BILLING_FEATURED = "Featured"
    BILLING_CHOICES = [
        (BILLING_CPM, "CPM"),
        (BILLING_CPC, "CPC"),
        (BILLING_SPONSORED, "Sponsored"),
        (BILLING_FEATURED, "Featured"),
    ]

    ad = models.ForeignKey(
        "ads.Advertisement",
        on_delete=models.CASCADE,
        db_index=True,
        related_name="revenue_events",
        null=True,
        blank=True,
    )
    billing_model = models.CharField(max_length=30, choices=BILLING_CHOICES, db_index=True)
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    revenue_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "ads_analytics"
        ordering = ["-timestamp"]
