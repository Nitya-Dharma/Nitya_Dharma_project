"""
Dashboard analytics service layer.

Computes all metrics for advertiser, pandit, and platform dashboards.
Uses aggregated tables where possible; raw events only with indexed filters and date bounds.
Phase-4: safe short-TTL caching for dashboard metrics; cache never blocks (miss → compute normally).
No PII; no modification to ad serving.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour, ExtractWeekDay
from django.utils import timezone

from ads_analytics.models import (
    AdImpression,
    AdClick,
    AdConversionIntent,
    AdDailyStats,
    AdPlacementStats,
    AdLocationStats,
    AdRevenueEvent,
)
from ads_analytics.queries import _date_range

# Phase-4: dashboard cache TTL (seconds). Short to keep data fresh; never blocks on miss.
DASHBOARD_CACHE_TTL = 90

# Phase-5: cache version bumped when aggregation runs; dashboard keys include version so
# aggregation completion effectively invalidates dashboard cache without delete_pattern.
DASHBOARD_CACHE_VERSION_KEY = "ads_analytics:agg:version"


def _dashboard_cache_version() -> int:
    """Current cache version; bumped by aggregation job so dashboard cache invalidates after agg."""
    try:
        from django.core.cache import cache
        return int(cache.get(DASHBOARD_CACHE_VERSION_KEY) or 0)
    except Exception:
        return 0


def invalidate_dashboard_cache() -> None:
    """
    Phase-5: Call after aggregation completes so dashboards see fresh aggregated data.
    Bumps cache version so existing dashboard cache keys are no longer used (they expire by TTL).
    Safe: no pattern delete required; cache miss → compute normally.
    """
    try:
        import time
        from django.core.cache import cache
        version = int(time.time())
        cache.set(DASHBOARD_CACHE_VERSION_KEY, version, timeout=86400 * 30)
    except Exception:
        pass


def _dashboard_cache_get(key: str) -> Optional[Any]:
    try:
        from django.core.cache import cache
        return cache.get(key)
    except Exception:
        return None


def _dashboard_cache_set(key: str, value: Any, timeout: int = DASHBOARD_CACHE_TTL) -> None:
    try:
        from django.core.cache import cache
        cache.set(key, value, timeout=timeout)
    except Exception:
        pass


def _advertiser_metrics_from_aggregated(ad_id: int, start: date, end: date, days: int) -> Optional[Dict[str, Any]]:
    """
    Build advertiser campaign metrics from AdDailyStats when aggregation has run.
    Returns None if no aggregated rows (fallback to raw).
    """
    totals = (
        AdDailyStats.objects.filter(
            ad_id=ad_id,
            date__gte=start,
            date__lte=end,
            placement_position__isnull=True,
            viewer_city__isnull=True,
        ).aggregate(impressions=Sum("impressions"), clicks=Sum("clicks"))
    )
    total_impressions = (totals["impressions"] or 0)
    total_clicks = (totals["clicks"] or 0)
    if total_impressions == 0 and total_clicks == 0:
        return None
    ctr = round(100.0 * total_clicks / total_impressions, 2) if total_impressions else 0.0

    placement_rows = (
        AdDailyStats.objects.filter(
            ad_id=ad_id,
            date__gte=start,
            date__lte=end,
        )
        .exclude(placement_position__isnull=True)
        .exclude(placement_position="")
        .values("placement_position")
        .annotate(impressions=Sum("impressions"), clicks=Sum("clicks"))
        .order_by("-impressions")[:10]
    )
    top_placements = []
    for p in placement_rows:
        imp = p["impressions"] or 0
        clk = p["clicks"] or 0
        top_placements.append({
            "placement_position": p["placement_position"],
            "placement_label": PLACEMENT_LABELS.get(p["placement_position"], p["placement_position"]),
            "impressions": imp,
            "clicks": clk,
            "ctr": round(100.0 * clk / imp, 2) if imp else 0.0,
        })

    return {
        "ad_id": ad_id,
        "days": days,
        "start": start,
        "end": end,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "ctr": ctr,
        "top_placements": top_placements,
        "top_creatives": [{"ad_id": ad_id, "impressions": total_impressions, "clicks": total_clicks, "ctr": ctr}],
        "location_performance": [],   # aggregated has no per-ad location; filled from raw below if needed
        "device_performance": [],     # no device in aggregates; filled from raw
    }


def _platform_metrics_from_aggregated(start: date, end: date, days: int) -> Optional[Dict[str, Any]]:
    """
    Build platform analytics from AdPlacementStats, AdLocationStats, AdDailyStats.
    Returns None if no aggregated data (fallback to raw).
    """
    placement_totals = (
        AdPlacementStats.objects.filter(date__gte=start, date__lte=end)
        .aggregate(impressions=Sum("impressions"), clicks=Sum("clicks"))
    )
    total_impressions = (placement_totals["impressions"] or 0)
    total_clicks = (placement_totals["clicks"] or 0)
    if total_impressions == 0 and total_clicks == 0:
        return None
    ctr = round(100.0 * total_clicks / total_impressions, 2) if total_impressions else 0.0

    placement_performance = list(
        AdPlacementStats.objects.filter(date__gte=start, date__lte=end)
        .values("placement_position")
        .annotate(impressions=Sum("impressions"), clicks=Sum("clicks"))
        .order_by("-impressions")
    )
    for p in placement_performance:
        imp = p["impressions"] or 0
        clk = p["clicks"] or 0
        p["placement_label"] = PLACEMENT_LABELS.get(p["placement_position"], p["placement_position"])
        p["clicks"] = clk
        p["ctr"] = round(100.0 * clk / imp, 2) if imp else 0.0

    top_cities = list(
        AdLocationStats.objects.filter(date__gte=start, date__lte=end)
        .exclude(viewer_city="")
        .values("viewer_city")
        .annotate(impressions=Sum("impressions"))
        .order_by("-impressions")[:15]
    )

    top_campaigns = list(
        AdDailyStats.objects.filter(
            date__gte=start,
            date__lte=end,
            placement_position__isnull=True,
            viewer_city__isnull=True,
        )
        .values("ad_id")
        .annotate(impressions=Sum("impressions"), clicks=Sum("clicks"))
        .order_by("-impressions")[:10]
    )
    for c in top_campaigns:
        imp = c["impressions"] or 0
        clk = c["clicks"] or 0
        c["ctr"] = round(100.0 * clk / imp, 2) if imp else 0.0

    return {
        "days": days,
        "start": start,
        "end": end,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "platform_ctr": ctr,
        "placement_performance": placement_performance,
        "top_cities": top_cities,
        "top_campaigns": top_campaigns,
    }


# Placement position to display label (for charts)
PLACEMENT_LABELS = {
    "top": "Homepage Banner",
    "sidebar": "Sidebar",
    "footer": "Footer",
    "in_content": "In Content",
    "dashboard_top": "Dashboard Top",
    "dashboard_sidebar": "Dashboard Sidebar",
}
WEEKDAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def _daterange_ts(days: int = 30, end_date: Optional[date] = None):
    start, end = _date_range(days, end_date)
    start_ts = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
    end_ts = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))
    return start_ts, end_ts, start, end


# --- Phase 1: Campaign / Advertiser metrics (ad_id = advertisement) ---


def _get_advertiser_campaign_metrics_uncached(ad_id: int, days: int, end_date: Optional[date], start_ts, end_ts, start, end) -> Dict[str, Any]:
    """Inner implementation without cache (used by get_advertiser_campaign_metrics)."""
    imp_qs = AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    click_qs = AdClick.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)

    out = _advertiser_metrics_from_aggregated(ad_id, start, end, days)
    if out is None:
        total_impressions = imp_qs.count()
        total_clicks = click_qs.count()
        ctr = round(100.0 * total_clicks / total_impressions, 2) if total_impressions else 0.0
        top_placements = list(
            imp_qs.values("placement_position")
            .annotate(impressions=Count("id"))
            .order_by("-impressions")[:10]
        )
        for p in top_placements:
            p["placement_label"] = PLACEMENT_LABELS.get(p["placement_position"], p["placement_position"])
            pos_clicks = click_qs.filter(placement_position=p["placement_position"]).count()
            p["clicks"] = pos_clicks
            p["ctr"] = round(100.0 * pos_clicks / p["impressions"], 2) if p["impressions"] else 0.0
        out = {
            "ad_id": ad_id,
            "days": days,
            "start": start,
            "end": end,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "ctr": ctr,
            "top_placements": top_placements,
            "top_creatives": [{"ad_id": ad_id, "impressions": total_impressions, "clicks": total_clicks, "ctr": ctr}],
            "location_performance": [],
            "device_performance": [],
        }

    # Location and device: only in raw events; always from raw
    location_performance = list(
        imp_qs.exclude(viewer_city="")
        .values("viewer_city", "viewer_state")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")[:15]
    )
    for loc in location_performance:
        loc_clicks = click_qs.filter(
            viewer_city=loc["viewer_city"],
            viewer_state=loc.get("viewer_state") or "",
        ).count()
        loc["clicks"] = loc_clicks
        loc["ctr"] = round(100.0 * loc_clicks / loc["impressions"], 2) if loc["impressions"] else 0.0
    out["location_performance"] = location_performance

    device_performance = []
    try:
        device_performance = list(
            imp_qs.values("device_type")
            .annotate(impressions=Count("id"))
            .order_by("-impressions")
        )
        for d in device_performance:
            d["clicks"] = 0
            d["ctr"] = 0.0
    except Exception:
        pass
    out["device_performance"] = device_performance

    return out


def get_advertiser_campaign_metrics(ad_id: int, days: int = 30, end_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Total impressions, clicks, CTR, top placements, top creatives (ads), location and device performance.
    Prefers AdDailyStats when aggregation has run; falls back to raw AdImpression/AdClick.
    Location and device always from raw (not in aggregated tables).
    Phase-4: result cached briefly (DASHBOARD_CACHE_TTL); cache miss computes normally.
    """
    start_ts, end_ts, start, end = _daterange_ts(days, end_date)
    cache_key = f"ads_analytics:dash:adv:{ad_id}:{days}:{end_date or ''}:v{_dashboard_cache_version()}"
    cached = _dashboard_cache_get(cache_key)
    if cached is not None:
        return cached
    result = _get_advertiser_campaign_metrics_uncached(ad_id, days, end_date, start_ts, end_ts, start, end)
    _dashboard_cache_set(cache_key, result)
    return result


def get_pandit_ad_analytics(pandit_id: int, days: int = 30, end_date: Optional[date] = None) -> Dict[str, Any]:
    """Ads displayed on pandit profile: impressions, clicks, CTR, top performing ads."""
    start_ts, end_ts, start, end = _daterange_ts(days, end_date)
    imp_qs = AdImpression.objects.filter(pandit_id=pandit_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    click_qs = AdClick.objects.filter(pandit_id=pandit_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    total_impressions = imp_qs.count()
    total_clicks = click_qs.count()
    ctr = round(100.0 * total_clicks / total_impressions, 2) if total_impressions else 0.0

    top_ads = list(
        imp_qs.values("ad_id")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")[:10]
    )
    for a in top_ads:
        a_clicks = click_qs.filter(ad_id=a["ad_id"]).count()
        a["clicks"] = a_clicks
        a["ctr"] = round(100.0 * a_clicks / a["impressions"], 2) if a["impressions"] else 0.0

    return {
        "pandit_id": pandit_id,
        "days": days,
        "start": start,
        "end": end,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "ctr": ctr,
        "top_ads_on_profile": top_ads,
    }


def get_platform_ad_analytics(days: int = 30, end_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Total platform impressions, clicks, CTR, placement performance, top cities, top campaigns (ads).
    Prefers AdPlacementStats, AdLocationStats, AdDailyStats when aggregation has run; falls back to raw.
    Phase-4: result cached briefly (DASHBOARD_CACHE_TTL); cache miss computes normally.
    """
    cache_key = f"ads_analytics:dash:plat:{days}:{end_date or ''}"
    cached = _dashboard_cache_get(cache_key)
    if cached is not None:
        return cached

    start_ts, end_ts, start, end = _daterange_ts(days, end_date)
    out = _platform_metrics_from_aggregated(start, end, days)
    if out is not None:
        _dashboard_cache_set(cache_key, out)
        return out

    imp_qs = AdImpression.objects.filter(timestamp__gte=start_ts, timestamp__lte=end_ts)
    click_qs = AdClick.objects.filter(timestamp__gte=start_ts, timestamp__lte=end_ts)
    total_impressions = imp_qs.count()
    total_clicks = click_qs.count()
    ctr = round(100.0 * total_clicks / total_impressions, 2) if total_impressions else 0.0

    placement_performance = list(
        imp_qs.values("placement_position")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")
    )
    for p in placement_performance:
        pos = p["placement_position"]
        p["placement_label"] = PLACEMENT_LABELS.get(pos, pos)
        p["clicks"] = click_qs.filter(placement_position=pos).count()
        p["ctr"] = round(100.0 * p["clicks"] / p["impressions"], 2) if p["impressions"] else 0.0

    top_cities = list(
        imp_qs.exclude(viewer_city="")
        .values("viewer_city")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")[:15]
    )
    top_campaigns = list(
        imp_qs.values("ad_id")
        .annotate(impressions=Count("id"))
        .order_by("-impressions")[:10]
    )
    for c in top_campaigns:
        c["clicks"] = click_qs.filter(ad_id=c["ad_id"]).count()
        c["ctr"] = round(100.0 * c["clicks"] / c["impressions"], 2) if c["impressions"] else 0.0

    result = {
        "days": days,
        "start": start,
        "end": end,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "platform_ctr": ctr,
        "placement_performance": placement_performance,
        "top_cities": top_cities,
        "top_campaigns": top_campaigns,
    }
    _dashboard_cache_set(cache_key, result)
    return result


# --- Phase 2: Time distribution ---


def get_hourly_impression_distribution(ad_id: int, days: int = 7) -> Dict[int, int]:
    """Impressions by hour (0–23). Chart-ready: {0: 120, 1: 85, ...}."""
    start_ts, end_ts, _, _ = _daterange_ts(days)
    qs = (
        AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
        .annotate(hour=ExtractHour("timestamp"))
        .values("hour")
        .annotate(impressions=Count("id"))
    )
    by_hour = {h: 0 for h in range(24)}
    for row in qs:
        by_hour[row["hour"]] = row["impressions"]
    return by_hour


def get_hourly_impression_chart_data(ad_id: int, days: int = 7) -> Dict[str, Any]:
    """Chart-ready: labels and data for line/bar chart."""
    by_hour = get_hourly_impression_distribution(ad_id, days)
    return {
        "labels": [f"{h}:00" for h in range(24)],
        "data": [by_hour[h] for h in range(24)],
    }


def get_weekday_performance(ad_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Impressions and clicks grouped by weekday (1=Sun, 7=Sat in Django)."""
    start_ts, end_ts, _, _ = _daterange_ts(days)
    imp = (
        AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
        .annotate(weekday=ExtractWeekDay("timestamp"))
        .values("weekday")
        .annotate(impressions=Count("id"))
    )
    click_qs = AdClick.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    by_day = {i: {"weekday": i, "name": WEEKDAY_NAMES[i - 1], "impressions": 0, "clicks": 0} for i in range(1, 8)}
    for row in imp:
        by_day[row["weekday"]]["impressions"] = row["impressions"]
    for row in click_qs.annotate(weekday=ExtractWeekDay("timestamp")).values("weekday").annotate(clicks=Count("id")):
        by_day[row["weekday"]]["clicks"] = row["clicks"]
    return [by_day[i] for i in range(1, 8)]


def get_weekday_chart_data(ad_id: int, days: int = 30) -> Dict[str, Any]:
    rows = get_weekday_performance(ad_id, days)
    return {
        "labels": [r["name"] for r in rows],
        "impressions": [r["impressions"] for r in rows],
        "clicks": [r["clicks"] for r in rows],
    }


def get_monthly_trends(ad_id: int, months: int = 6) -> List[Dict[str, Any]]:
    """Impression and click trends per month from AdDailyStats."""
    end = timezone.now().date()
    start = end - timedelta(days=months * 31)
    rows = (
        AdDailyStats.objects.filter(
            ad_id=ad_id,
            date__gte=start,
            date__lte=end,
            placement_position__isnull=True,
            viewer_city__isnull=True,
        )
        .order_by("date")
        .values("date", "impressions", "clicks")
    )
    by_month: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        key = r["date"].strftime("%Y-%m")
        if key not in by_month:
            by_month[key] = {"month": key, "impressions": 0, "clicks": 0}
        by_month[key]["impressions"] += r["impressions"]
        by_month[key]["clicks"] += r["clicks"]
    return sorted(by_month.values(), key=lambda x: x["month"])


def get_monthly_trend_chart_data(ad_id: int, months: int = 6) -> Dict[str, Any]:
    """Chart data from AdDailyStats (aggregated). Phase-4: cached briefly."""
    cache_key = f"ads_analytics:dash:monthly:{ad_id}:{months}:v{_dashboard_cache_version()}"
    cached = _dashboard_cache_get(cache_key)
    if cached is not None:
        return cached
    trends = get_monthly_trends(ad_id, months)
    result = {
        "labels": [t["month"] for t in trends],
        "impressions": [t["impressions"] for t in trends],
        "clicks": [t["clicks"] for t in trends],
    }
    _dashboard_cache_set(cache_key, result)
    return result


def get_daily_trend_chart_data_from_aggregated(ad_id: int, days: int = 30, end_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Daily impression/click trend from AdDailyStats (no raw event scan).
    Use for campaign daily time-series when aggregation is available.
    Returns labels (date strings), impressions, clicks lists; empty if no aggregated data.
    """
    start, end = _date_range(days, end_date)
    rows = (
        AdDailyStats.objects.filter(
            ad_id=ad_id,
            date__gte=start,
            date__lte=end,
            placement_position__isnull=True,
            viewer_city__isnull=True,
        )
        .order_by("date")
        .values("date", "impressions", "clicks")
    )
    labels = []
    impressions = []
    clicks = []
    for r in rows:
        labels.append(r["date"].strftime("%Y-%m-%d"))
        impressions.append(r["impressions"])
        clicks.append(r["clicks"])
    return {"labels": labels, "impressions": impressions, "clicks": clicks}


# --- Phase 3: Location analytics ---


def get_city_performance(ad_id: int, days: int = 30, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """City, impressions, clicks, CTR. Phase-4: result cached briefly; cache miss computes normally."""
    cache_key = f"ads_analytics:dash:city:{ad_id}:{days}:{end_date or ''}:v{_dashboard_cache_version()}"
    cached = _dashboard_cache_get(cache_key)
    if cached is not None:
        return cached
    start_ts, end_ts, _, _ = _daterange_ts(days, end_date)
    imp = (
        AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
        .exclude(viewer_city="")
        .values("viewer_city")
        .annotate(impressions=Count("id"))
    )
    click_qs = AdClick.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    result = []
    for row in imp:
        city = row["viewer_city"]
        clicks = click_qs.filter(viewer_city=city).count()
        result.append({
            "city": city,
            "impressions": row["impressions"],
            "clicks": clicks,
            "ctr": round(100.0 * clicks / row["impressions"], 2) if row["impressions"] else 0.0,
        })
    result = sorted(result, key=lambda x: -x["impressions"])[:20]
    _dashboard_cache_set(cache_key, result)
    return result


def get_area_performance(ad_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Area/locality breakdown."""
    start_ts, end_ts, _, _ = _daterange_ts(days)
    imp = (
        AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
        .exclude(viewer_area="")
        .values("viewer_area", "viewer_city")
        .annotate(impressions=Count("id"))
    )
    click_qs = AdClick.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    result = []
    for row in imp:
        area, city = row["viewer_area"], row.get("viewer_city") or ""
        clicks = click_qs.filter(viewer_area=area, viewer_city=city).count()
        result.append({
            "area": area,
            "city": city,
            "impressions": row["impressions"],
            "clicks": clicks,
            "ctr": round(100.0 * clicks / row["impressions"], 2) if row["impressions"] else 0.0,
        })
    return sorted(result, key=lambda x: -x["impressions"])[:20]


def get_state_performance(ad_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """State-level performance."""
    start_ts, end_ts, _, _ = _daterange_ts(days)
    imp = (
        AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
        .exclude(viewer_state="")
        .values("viewer_state")
        .annotate(impressions=Count("id"))
    )
    click_qs = AdClick.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    result = []
    for row in imp:
        state = row["viewer_state"]
        clicks = click_qs.filter(viewer_state=state).count()
        result.append({
            "state": state,
            "impressions": row["impressions"],
            "clicks": clicks,
            "ctr": round(100.0 * clicks / row["impressions"], 2) if row["impressions"] else 0.0,
        })
    return sorted(result, key=lambda x: -x["impressions"])[:20]


def get_city_heatmap_data(ad_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Chart-ready list of {city, impressions, clicks} for heatmaps."""
    return get_city_performance(ad_id, days)


# --- Phase 4: Placement performance (platform) ---


def get_placement_performance(days: int = 30) -> List[Dict[str, Any]]:
    """Homepage banner, Sidebar, Feed, etc. with impressions and CTR."""
    data = get_platform_ad_analytics(days=days)
    return data["placement_performance"]


def get_placement_chart_data(days: int = 30) -> Dict[str, Any]:
    """Bar chart: placements vs CTR."""
    perf = get_placement_performance(days)
    return {
        "placements": [p.get("placement_label") or p["placement_position"] for p in perf],
        "impressions": [p["impressions"] for p in perf],
        "clicks": [p["clicks"] for p in perf],
        "ctr_values": [p["ctr"] for p in perf],
    }


# --- Phase 5: Creative performance (per-ad; campaign_id optional) ---


def get_creative_performance(campaign_id: Optional[str] = None, ad_id: Optional[int] = None, days: int = 30) -> List[Dict[str, Any]]:
    """
    Per-ad (creative) metrics. If campaign_id given, filter by events with that campaign_id.
    Otherwise single ad_id or all ads.
    """
    start_ts, end_ts, _, _ = _daterange_ts(days)
    imp_qs = AdImpression.objects.filter(timestamp__gte=start_ts, timestamp__lte=end_ts)
    click_qs = AdClick.objects.filter(timestamp__gte=start_ts, timestamp__lte=end_ts)
    if campaign_id:
        imp_qs = imp_qs.filter(campaign_id=campaign_id)
        click_qs = click_qs.filter(campaign_id=campaign_id)
    elif ad_id:
        imp_qs = imp_qs.filter(ad_id=ad_id)
        click_qs = click_qs.filter(ad_id=ad_id)

    creatives = list(imp_qs.values("ad_id").annotate(impressions=Count("id")).order_by("-impressions")[:20])
    for c in creatives:
        c["clicks"] = click_qs.filter(ad_id=c["ad_id"]).count()
        c["ctr"] = round(100.0 * c["clicks"] / c["impressions"], 2) if c["impressions"] else 0.0
    return creatives


# --- Phase 6: Conversion funnel ---


def get_ad_conversion_funnel(ad_id: int, days: int = 30) -> Dict[str, Any]:
    """
    Funnel: impressions -> clicks -> profile views -> booking intents.
    Uses AdImpression, AdClick, AdConversionIntent (conversion_type).
    """
    start_ts, end_ts, _, _ = _daterange_ts(days)
    impressions = AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts).count()
    clicks = AdClick.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts).count()
    conversions = AdConversionIntent.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    profile_views = conversions.filter(conversion_type=AdConversionIntent.CONVERSION_PROFILE_VIEW).count()
    booking_intents = conversions.filter(conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT).count()

    return {
        "impressions": impressions,
        "clicks": clicks,
        "profile_views": profile_views,
        "booking_intents": booking_intents,
        "click_rate": round(100.0 * clicks / impressions, 2) if impressions else 0.0,
        "profile_view_rate": round(100.0 * profile_views / clicks, 2) if clicks else 0.0,
        "booking_intent_rate": round(100.0 * booking_intents / clicks, 2) if clicks else 0.0,
    }


def get_funnel_chart_data(ad_id: int, days: int = 30) -> Dict[str, Any]:
    f = get_ad_conversion_funnel(ad_id, days)
    return {
        "labels": ["Impressions", "Clicks", "Profile views", "Booking intents"],
        "data": [f["impressions"], f["clicks"], f["profile_views"], f["booking_intents"]],
    }


def get_campaign_conversion_metrics(
    campaign_id: Optional[str],
    days: int = 30,
) -> Dict[str, Any]:
    """
    Historical Campaign conversion counts via AdConversionIntent.campaign_id.

    Filters by the persisted event campaign_id string (same convention as
    get_creative_performance). Does not use Advertisement.campaign.
    NULL / blank campaign_id rows are never attributed to a Campaign.
    """
    start_ts, end_ts, start, end = _daterange_ts(days)
    empty = {
        "campaign_id": campaign_id,
        "days": days,
        "start": start,
        "end": end,
        "conversion_count": 0,
        "booking_intent_count": 0,
        "other_count": 0,
        "profile_view_count": 0,
    }
    if campaign_id is None:
        return empty
    cid = str(campaign_id).strip()
    if not cid:
        return empty

    qs = AdConversionIntent.objects.filter(
        campaign_id=cid,
        timestamp__gte=start_ts,
        timestamp__lte=end_ts,
    )
    booking_intent_count = qs.filter(
        conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT
    ).count()
    other_count = qs.filter(
        conversion_type=AdConversionIntent.CONVERSION_OTHER
    ).count()
    profile_view_count = qs.filter(
        conversion_type=AdConversionIntent.CONVERSION_PROFILE_VIEW
    ).count()
    return {
        "campaign_id": cid,
        "days": days,
        "start": start,
        "end": end,
        "conversion_count": qs.count(),
        "booking_intent_count": booking_intent_count,
        "other_count": other_count,
        "profile_view_count": profile_view_count,
    }


def get_campaign_delivery_metrics(
    campaign_id: Optional[str],
    days: int = 30,
) -> Dict[str, Any]:
    """
    Historical Campaign delivery counts via AdImpression/AdClick.campaign_id.

    Filters by the persisted event campaign_id string (same convention as
    get_campaign_conversion_metrics / get_creative_performance). Does not use
    Advertisement.campaign. NULL / blank campaign_id rows are never attributed.
    """
    start_ts, end_ts, start, end = _daterange_ts(days)
    empty = {
        "campaign_id": campaign_id,
        "days": days,
        "start": start,
        "end": end,
        "impressions": 0,
        "clicks": 0,
        "ctr": 0.0,
    }
    if campaign_id is None:
        return empty
    cid = str(campaign_id).strip()
    if not cid:
        return empty

    impressions = AdImpression.objects.filter(
        campaign_id=cid,
        timestamp__gte=start_ts,
        timestamp__lte=end_ts,
    ).count()
    clicks = AdClick.objects.filter(
        campaign_id=cid,
        timestamp__gte=start_ts,
        timestamp__lte=end_ts,
    ).count()
    ctr = round(100.0 * clicks / impressions, 2) if impressions else 0.0
    return {
        "campaign_id": cid,
        "days": days,
        "start": start,
        "end": end,
        "impressions": impressions,
        "clicks": clicks,
        "ctr": ctr,
    }


# --- Phase 7: Device and user type ---


def get_device_distribution(ad_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Mobile, desktop, tablet impressions. Clicks by device not available (AdClick has no device_type)."""
    start_ts, end_ts, _, _ = _daterange_ts(days)
    result = []
    try:
        imp = (
            AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
            .values("device_type")
            .annotate(impressions=Count("id"))
        )
        for row in imp:
            result.append({
                "device_type": row.get("device_type") or "unknown",
                "impressions": row["impressions"],
                "clicks": 0,  # AdClick model has no device_type field
            })
    except Exception:
        pass
    return result


def get_user_type_distribution(ad_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """Guest vs registered (user_id null vs non-null). Pandits are users; no separate role in events."""
    start_ts, end_ts, _, _ = _daterange_ts(days)
    imp_qs = AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    guest_imp = imp_qs.filter(user_id__isnull=True).count()
    registered_imp = imp_qs.filter(user_id__isnull=False).count()
    click_qs = AdClick.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts)
    guest_clicks = click_qs.filter(user_id__isnull=True).count()
    registered_clicks = click_qs.filter(user_id__isnull=False).count()
    return [
        {"user_type": "guest", "impressions": guest_imp, "clicks": guest_clicks},
        {"user_type": "registered", "impressions": registered_imp, "clicks": registered_clicks},
    ]


# --- Phase 8: Revenue ---


def calculate_cpm_revenue(ad_id: int, cpm_rate: float, days: int = 30) -> Dict[str, Any]:
    """revenue = impressions / 1000 * cpm_rate."""
    start_ts, end_ts, start, end = _daterange_ts(days)
    impressions = AdImpression.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts).count()
    revenue = (impressions / 1000.0) * float(cpm_rate)
    return {"ad_id": ad_id, "impressions": impressions, "cpm_rate": cpm_rate, "revenue": round(revenue, 2)}


def calculate_cpc_revenue(ad_id: int, cpc_rate: float, days: int = 30) -> Dict[str, Any]:
    """revenue = clicks * cpc_rate."""
    start_ts, end_ts, _, _ = _daterange_ts(days)
    clicks = AdClick.objects.filter(ad_id=ad_id, timestamp__gte=start_ts, timestamp__lte=end_ts).count()
    revenue = clicks * float(cpc_rate)
    return {"ad_id": ad_id, "clicks": clicks, "cpc_rate": cpc_rate, "revenue": round(revenue, 2)}


def get_revenue_summary(ad_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
    """Sum of AdRevenueEvent for the period (optionally for one ad)."""
    start = timezone.now() - timedelta(days=days)
    qs = AdRevenueEvent.objects.filter(timestamp__gte=start)
    if ad_id is not None:
        qs = qs.filter(ad_id=ad_id)
    total = qs.aggregate(total_revenue=Sum("revenue_amount"), total_impressions=Sum("impressions"), total_clicks=Sum("clicks"))
    return {
        "total_revenue": float(total["total_revenue"] or 0),
        "total_impressions": total["total_impressions"] or 0,
        "total_clicks": total["total_clicks"] or 0,
    }


def calculate_sponsored_listing_revenue(listing_id: int) -> Dict[str, Any]:
    """Placeholder: flat fee. Implement when SponsoredListing model exists."""
    return {"listing_id": listing_id, "revenue": 0, "model": "flat_fee"}


def calculate_featured_pandit_revenue(pandit_id: int) -> Dict[str, Any]:
    """Placeholder: subscription. Implement when FeaturedPandit billing exists."""
    return {"pandit_id": pandit_id, "revenue": 0, "model": "subscription"}
