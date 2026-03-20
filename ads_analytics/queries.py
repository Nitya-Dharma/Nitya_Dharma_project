"""
Dashboard KPI queries for advertiser, pandit, and platform analytics.

Aligned with docs/advertisement_analytics_detailed_kpis.md.
No modification to ad serving; read-only aggregations from event/aggregate tables.
"""

from datetime import date, timedelta
from typing import Optional

from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour
from django.utils import timezone

from .models import AdImpression, AdClick, AdDailyStats, AdPlacementStats, AdLocationStats


def _date_range(days: int = 30, end_date: Optional[date] = None):
    if end_date is None:
        end_date = timezone.now().date()
    start = end_date - timedelta(days=max(0, days))
    return start, end_date


# --- Advertiser / campaign KPIs ---


def advertiser_kpis(ad_id: int, days: int = 30, end_date: Optional[date] = None) -> dict:
    """
    Total impressions, clicks, CTR, top placements, device breakdown, location summary.
    Uses raw events for flexibility; can be switched to AdDailyStats for speed on large data.
    """
    start, end = _date_range(days, end_date)
    start_ts = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
    end_ts = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))

    impressions = AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    clicks = AdClick.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    imp_count = impressions.count()
    click_count = clicks.count()
    ctr = round(100.0 * click_count / imp_count, 2) if imp_count else 0.0

    # Top placements by impressions
    top_placements = (
        impressions.values("placement_position")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")[:10]
    )
    # Device breakdown
    device_breakdown = (
        impressions.values("device_type")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")
    )
    # Location (city) summary
    top_cities = (
        impressions.exclude(viewer_city="")
        .values("viewer_city")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")[:10]
    )

    return {
        "ad_id": ad_id,
        "days": days,
        "start": start,
        "end": end,
        "total_impressions": imp_count,
        "total_clicks": click_count,
        "ctr": ctr,
        "top_placements": list(top_placements),
        "device_breakdown": list(device_breakdown),
        "top_cities": list(top_cities),
    }


def advertiser_daily_trend(ad_id: int, days: int = 30) -> list:
    """Daily impression/click trend for charts."""
    start, end = _date_range(days)
    rows = (
        AdDailyStats.objects.filter(ad_id=ad_id, date__gte=start, date__lte=end)
        .filter(placement_position__isnull=True, viewer_city__isnull=True)
        .order_by("date")
        .values("date", "impressions", "clicks")
    )
    return list(rows)


# --- Pandit dashboard KPIs ---


def pandit_ad_kpis(pandit_id: int, days: int = 30, end_date: Optional[date] = None) -> dict:
    """
    Ads displayed on this pandit's profile: impressions, clicks, CTR, visitor location.
    """
    start, end = _date_range(days, end_date)
    start_ts = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
    end_ts = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))

    impressions = AdImpression.objects.filter(
        pandit_id=pandit_id, timestamp__gte=start_ts, timestamp__lte=end_ts
    )
    clicks = AdClick.objects.filter(
        pandit_id=pandit_id, timestamp__gte=start_ts, timestamp__lte=end_ts
    )
    imp_count = impressions.count()
    click_count = clicks.count()
    ctr = round(100.0 * click_count / imp_count, 2) if imp_count else 0.0

    city_breakdown = (
        impressions.exclude(viewer_city="")
        .values("viewer_city")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")[:10]
    )

    return {
        "pandit_id": pandit_id,
        "days": days,
        "start": start,
        "end": end,
        "impressions_on_profile": imp_count,
        "clicks_from_profile": click_count,
        "ctr": ctr,
        "viewer_city_breakdown": list(city_breakdown),
    }


# --- Platform-level KPIs ---


def platform_ad_kpis(days: int = 30, end_date: Optional[date] = None) -> dict:
    """
    Total platform impressions, clicks, overall CTR, placement performance, top cities.
    """
    start, end = _date_range(days, end_date)
    start_ts = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
    end_ts = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))

    impressions = AdImpression.objects.filter(timestamp__gte=start_ts, timestamp__lte=end_ts)
    clicks = AdClick.objects.filter(timestamp__gte=start_ts, timestamp__lte=end_ts)
    imp_count = impressions.count()
    click_count = clicks.count()
    ctr = round(100.0 * click_count / imp_count, 2) if imp_count else 0.0

    placement_performance = (
        impressions.values("placement_position")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")
    )
    # Add clicks and CTR per placement
    placement_list = []
    for row in placement_performance:
        pos = row["placement_position"]
        place_clicks = clicks.filter(placement_position=pos).count()
        place_ctr = round(100.0 * place_clicks / row["impressions"], 2) if row["impressions"] else 0.0
        placement_list.append({
            "placement_position": pos,
            "impressions": row["impressions"],
            "clicks": place_clicks,
            "ctr": place_ctr,
        })

    top_cities = (
        impressions.exclude(viewer_city="")
        .values("viewer_city")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")[:15]
    )

    return {
        "days": days,
        "start": start,
        "end": end,
        "total_impressions": imp_count,
        "total_clicks": click_count,
        "overall_ctr": ctr,
        "placement_performance": placement_list,
        "top_cities": list(top_cities),
    }


def platform_daily_trend(days: int = 30) -> list:
    """Platform-wide daily totals from AdPlacementStats rolled up."""
    start, end = _date_range(days)
    rows = (
        AdPlacementStats.objects.filter(date__gte=start, date__lte=end)
        .values("date")
        .annotate(impressions=Sum("impressions"), clicks=Sum("clicks"))
        .order_by("date")
    )
    return list(rows)


def platform_hourly_distribution(days: int = 7) -> list:
    """Impressions by hour of day (0-23) for peak traffic. Uses raw events."""
    start, end = _date_range(days)
    start_ts = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
    end_ts = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))
    qs = (
        AdImpression.objects.filter(timestamp__gte=start_ts, timestamp__lte=end_ts)
        .annotate(hour=ExtractHour("timestamp"))
        .values("hour")
        .annotate(impressions=Count("id"))
        .order_by("hour")
    )
    return list(qs)
