"""
Daily aggregation of ad events into AdDailyStats, AdPlacementStats, AdLocationStats.

Run via: python manage.py aggregate_ad_metrics [--date YYYY-MM-DD] [--days N]
Or schedule with cron/Celery. Does not modify ad serving or event tables.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from django.db.models import Count
from django.utils import timezone

from .models import AdImpression, AdClick, AdDailyStats, AdPlacementStats, AdLocationStats

logger = logging.getLogger(__name__)


def aggregate_daily_ad_metrics(
    target_date: Optional[date] = None,
    *,
    days: int = 1,
) -> dict:
    """
    Aggregate raw AdImpression and AdClick into daily stats for the given date(s).
    Returns summary dict with counts of rows created/updated.
    """
    if target_date is None:
        target_date = timezone.now().date()
    if days < 1:
        days = 1

    date_from = target_date - timedelta(days=days - 1)
    logger.info(
        "ads_analytics aggregation job start: date_from=%s, date_to=%s, days=%s",
        date_from,
        target_date,
        days,
    )

    total_daily = 0
    total_placement = 0
    total_location = 0

    for d in range(days):
        dte = target_date - timedelta(days=d)
        a, b, c = _aggregate_one_day(dte)
        total_daily += a
        total_placement += b
        total_location += c

    result = {
        "date_from": date_from,
        "date_to": target_date,
        "ad_daily_stats": total_daily,
        "placement_stats": total_placement,
        "location_stats": total_location,
    }
    logger.info(
        "ads_analytics aggregation job complete: ad_daily_stats=%s, placement_stats=%s, location_stats=%s",
        total_daily,
        total_placement,
        total_location,
    )
    return result


def _aggregate_one_day(dte: date) -> tuple:
    """Returns (daily_updated, placement_updated, location_updated)."""
    start = timezone.make_aware(timezone.datetime.combine(dte, timezone.datetime.min.time()))
    end = start + timedelta(days=1)

    imp_count = AdImpression.objects.filter(timestamp__gte=start, timestamp__lt=end).count()
    click_count = AdClick.objects.filter(timestamp__gte=start, timestamp__lt=end).count()
    logger.debug(
        "ads_analytics aggregate one day %s: raw impressions=%s, raw clicks=%s",
        dte,
        imp_count,
        click_count,
    )

    # --- Per-ad totals (one row per ad per day, null placement/city/state = totals) ---
    ad_totals = (
        AdImpression.objects.filter(timestamp__gte=start, timestamp__lt=end)
        .values("ad_id")
        .annotate(impressions=Count("id"))
    )
    click_totals = (
        AdClick.objects.filter(timestamp__gte=start, timestamp__lt=end)
        .values("ad_id")
        .annotate(clicks=Count("id"))
    )
    click_map = {r["ad_id"]: r["clicks"] for r in click_totals}
    # Approximate unique: max of distinct user_id and distinct session_id
    unique_by_user = {
        r["ad_id"]: r["n"]
        for r in AdImpression.objects.filter(timestamp__gte=start, timestamp__lt=end)
        .values("ad_id")
        .annotate(n=Count("user_id", distinct=True))
    }
    unique_by_session = {
        r["ad_id"]: r["n"]
        for r in AdImpression.objects.filter(timestamp__gte=start, timestamp__lt=end)
        .values("ad_id")
        .annotate(n=Count("session_id", distinct=True))
    }

    daily_count = 0
    for r in ad_totals:
        ad_id = r["ad_id"]
        imp = r["impressions"]
        clicks = click_map.get(ad_id, 0)
        uniq = max(unique_by_user.get(ad_id, 0), unique_by_session.get(ad_id, 0))
        obj = AdDailyStats.objects.filter(
            date=dte,
            ad_id=ad_id,
            placement_position__isnull=True,
            viewer_city__isnull=True,
            viewer_state__isnull=True,
        ).first()
        if obj:
            obj.impressions = imp
            obj.clicks = clicks
            obj.unique_users = uniq
            obj.save()
        else:
            AdDailyStats.objects.create(
                date=dte,
                ad_id=ad_id,
                placement_position=None,
                viewer_city=None,
                viewer_state=None,
                impressions=imp,
                clicks=clicks,
                unique_users=uniq,
            )
        daily_count += 1

    # --- Placement totals (one row per placement per day) ---
    placement_count = 0
    for row in (
        AdImpression.objects.filter(timestamp__gte=start, timestamp__lt=end)
        .values("placement_position")
        .annotate(impressions=Count("id"))
    ):
        placement = row["placement_position"]
        clicks = AdClick.objects.filter(
            timestamp__gte=start, timestamp__lt=end, placement_position=placement
        ).count()
        AdPlacementStats.objects.update_or_create(
            date=dte,
            placement_position=placement,
            defaults={"impressions": row["impressions"], "clicks": clicks},
        )
        placement_count += 1

    # --- Location totals (one row per city/state per day, skip empty city) ---
    location_count = 0
    for row in (
        AdImpression.objects.filter(timestamp__gte=start, timestamp__lt=end)
        .exclude(viewer_city="")
        .values("viewer_city", "viewer_state")
        .annotate(impressions=Count("id"))
    ):
        city = row["viewer_city"] or ""
        state = row["viewer_state"] or ""
        clicks = AdClick.objects.filter(
            timestamp__gte=start,
            timestamp__lt=end,
            viewer_city=city,
            viewer_state=state,
        ).count()
        AdLocationStats.objects.update_or_create(
            date=dte,
            viewer_city=city,
            viewer_state=state,
            defaults={"impressions": row["impressions"], "clicks": clicks},
        )
        location_count += 1

    return (daily_count, placement_count, location_count)
