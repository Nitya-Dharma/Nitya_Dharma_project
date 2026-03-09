"""
Daily aggregation of raw behavior data into intelligence tables.
Run in batch only; do not run during request handling.
Raw events older than 90 days may be archived; aggregated tables retain historical data.

Idempotent: all writers use update_or_create on natural keys (no duplicate rows).
Transaction-safe: run_daily_behavior_aggregation runs in a single transaction.
Late events: pass target_dates=[yesterday, day_before] to re-aggregate last 2 days.
"""
import logging
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Count, Avg
from django.utils import timezone

from behavior_engine.models import (
    UserBehaviorEvent,
    UserContentInteraction,
    UserFeedImpression,
    UserInterestSignal,
    PanditEngagementDaily,
    SearchTrendDaily,
    UserEngagementDaily,
    ContentInteractionDaily,
    UserInterestAggregate,
    EVENT_PANDIT_PROFILE_VIEW,
    EVENT_SEARCH_RESULT_CLICK,
    EVENT_BOOKING_INTENT_SENT,
    EVENT_REVIEW_VIEW,
    EVENT_PAGE_VIEW,
    EVENT_SEARCH_QUERY,
)

logger = logging.getLogger(__name__)


def _date_range(target_date):
    """Return (start, end) datetime for target_date (in local date)."""
    from datetime import datetime as dt
    start = timezone.make_aware(dt.combine(target_date, dt.min.time()))
    end = start + timedelta(days=1)
    return start, end


def compute_daily_pandit_engagement(target_date):
    """Aggregate pandit engagement for target_date. Idempotent: update_or_create(pandit_id, date)."""
    start, end = _date_range(target_date)
    # From UserBehaviorEvent: object_type=pandit_profile, created_at in [start, end)
    qs = (
        UserBehaviorEvent.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            object_type="pandit_profile",
            object_id__isnull=False,
        )
        .values("object_id", "event_type")
        .annotate(cnt=Count("id"))
    )
    by_pandit = {}
    for row in qs:
        pid = row["object_id"]
        if pid not in by_pandit:
            by_pandit[pid] = {
                "profile_views": 0,
                "search_clicks": 0,
                "booking_intents": 0,
                "review_views": 0,
            }
        if row["event_type"] == EVENT_PANDIT_PROFILE_VIEW:
            by_pandit[pid]["profile_views"] += row["cnt"]
        elif row["event_type"] == EVENT_SEARCH_RESULT_CLICK:
            by_pandit[pid]["search_clicks"] += row["cnt"]
        elif row["event_type"] == EVENT_BOOKING_INTENT_SENT:
            by_pandit[pid]["booking_intents"] += row["cnt"]
        elif row["event_type"] == EVENT_REVIEW_VIEW:
            by_pandit[pid]["review_views"] += row["cnt"]
    # Dwell from UserContentInteraction
    dwell_qs = (
        UserContentInteraction.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            content_type="pandit_profile",
        )
        .values("content_id")
        .annotate(avg_dwell=Avg("dwell_time_ms"))
    )
    for row in dwell_qs:
        pid = row["content_id"]
        if pid not in by_pandit:
            by_pandit[pid] = {"profile_views": 0, "search_clicks": 0, "booking_intents": 0, "review_views": 0}
        by_pandit[pid]["avg_dwell_time_ms"] = int(row["avg_dwell"] or 0)
    for pid, data in by_pandit.items():
        avg_dwell = data.get("avg_dwell_time_ms", 0)
        score = (
            data["profile_views"] * 1
            + data["search_clicks"] * 2
            + data["booking_intents"] * 4
            + data["review_views"] * 1
        )
        PanditEngagementDaily.objects.update_or_create(
            pandit_id=pid,
            date=target_date,
            defaults={
                "profile_views": data["profile_views"],
                "search_clicks": data["search_clicks"],
                "booking_intents": data["booking_intents"],
                "review_views": data["review_views"],
                "avg_dwell_time_ms": avg_dwell,
                "engagement_score": score,
            },
        )
    return len(by_pandit)


def compute_search_trends(target_date):
    """Aggregate search trends for target_date. Idempotent: update_or_create(query, date)."""
    start, end = _date_range(target_date)
    # Search count from UserBehaviorEvent event_type=search_query, metadata.query
    try:
        from search.models import SearchResultClick
    except ImportError:
        SearchResultClick = None
    query_counts = {}
    for ev in UserBehaviorEvent.objects.filter(
        created_at__gte=start, created_at__lt=end, event_type=EVENT_SEARCH_QUERY
    ).iterator(chunk_size=500):
        q = (ev.metadata or {}).get("query") or ""
        q = (q[:200]).strip() or "unknown"
        query_counts[q] = query_counts.get(q, 0) + 1
    click_counts = {}
    if SearchResultClick is not None:
        for row in (
            SearchResultClick.objects.filter(clicked_at__gte=start, clicked_at__lt=end)
            .values("query")
            .annotate(cnt=Count("id"))
        ):
            q = (row["query"] or "")[:200].strip() or "unknown"
            click_counts[q] = row["cnt"]
    all_queries = set(query_counts) | set(click_counts)
    for q in all_queries:
        SearchTrendDaily.objects.update_or_create(
            query=q,
            date=target_date,
            defaults={
                "search_count": query_counts.get(q, 0),
                "click_count": click_counts.get(q, 0),
                "conversion_count": 0,
            },
        )
    return len(all_queries)


def compute_user_engagement(target_date):
    """Aggregate platform-wide engagement for target_date. Idempotent: update_or_create(date)."""
    start, end = _date_range(target_date)
    events = UserBehaviorEvent.objects.filter(created_at__gte=start, created_at__lt=end)
    active_users = events.filter(user_id__isnull=False).values("user_id").distinct().count()
    total_page_views = events.filter(event_type=EVENT_PAGE_VIEW).count()
    total_searches = events.filter(event_type=EVENT_SEARCH_QUERY).count()
    total_sessions = events.filter(session_id__isnull=False).exclude(session_id="").values("session_id").distinct().count()
    total_interactions = events.count()
    # Approximate session duration from UserSessionAnalytics if present
    try:
        from behavior_engine.models import UserSessionAnalytics
        sess = UserSessionAnalytics.objects.filter(
            session_start__gte=start, session_start__lt=end
        ).aggregate(avg_ms=Avg("total_dwell_time_ms"))
        avg_session_duration_ms = int(sess["avg_ms"] or 0)
    except Exception:
        avg_session_duration_ms = 0
    UserEngagementDaily.objects.update_or_create(
        date=target_date,
        defaults={
            "active_users": active_users,
            "total_sessions": total_sessions,
            "total_page_views": total_page_views,
            "total_searches": total_searches,
            "total_interactions": total_interactions,
            "avg_session_duration_ms": avg_session_duration_ms,
        },
    )
    return 1


def compute_content_interactions(target_date):
    """Aggregate content interactions for target_date. Idempotent: update_or_create(content_type, content_id, date)."""
    start, end = _date_range(target_date)
    # UserContentInteraction: impressions (view/impression), clicks, saves, shares; avg_dwell
    qs = (
        UserContentInteraction.objects.filter(created_at__gte=start, created_at__lt=end)
        .values("content_type", "content_id", "interaction_type")
        .annotate(cnt=Count("id"))
    )
    by_content = {}
    for row in qs:
        key = (row["content_type"], row["content_id"])
        if key not in by_content:
            by_content[key] = {"impressions": 0, "clicks": 0, "saves": 0, "shares": 0, "dwell_sum": 0, "dwell_n": 0}
        it = (row["interaction_type"] or "").lower()
        c = row["cnt"]
        if it in ("view", "impression"):
            by_content[key]["impressions"] += c
        elif it == "click":
            by_content[key]["clicks"] += c
        elif it == "save":
            by_content[key]["saves"] += c
        elif it == "share":
            by_content[key]["shares"] += c
    dwell_qs = (
        UserContentInteraction.objects.filter(
            created_at__gte=start, created_at__lt=end, dwell_time_ms__isnull=False
        )
        .values("content_type", "content_id")
        .annotate(avg_dwell=Avg("dwell_time_ms"))
    )
    for row in dwell_qs:
        key = (row["content_type"], row["content_id"])
        if key not in by_content:
            by_content[key] = {"impressions": 0, "clicks": 0, "saves": 0, "shares": 0, "dwell_sum": 0, "dwell_n": 0}
        by_content[key]["avg_dwell_time_ms"] = int(row["avg_dwell"] or 0)
    for (ct, cid), data in by_content.items():
        avg_dwell = data.get("avg_dwell_time_ms", 0)
        ContentInteractionDaily.objects.update_or_create(
            content_type=ct[:50],
            content_id=cid,
            date=target_date,
            defaults={
                "impressions": data["impressions"],
                "clicks": data["clicks"],
                "saves": data["saves"],
                "shares": data["shares"],
                "avg_dwell_time_ms": avg_dwell,
            },
        )
    return len(by_content)


def update_user_interest_signals():
    """Sync UserInterestSignal into UserInterestAggregate. Idempotent: update_or_create(user, interest_type, interest_value)."""
    updated = 0
    for sig in UserInterestSignal.objects.select_related("user").iterator(chunk_size=500):
        _, created = UserInterestAggregate.objects.update_or_create(
            user=sig.user,
            interest_type=sig.interest_type,
            interest_value=sig.interest_value,
            defaults={
                "score": sig.score,
                "interaction_count": 0,
            },
        )
        updated += 0 if created else 1
    return updated


def run_daily_behavior_aggregation(target_date=None, target_dates=None):
    """
    Run all daily aggregations with per-step transactions. Idempotent and safe to run multiple times.

    Args:
        target_date: Single date to aggregate (default: yesterday).
        target_dates: Optional list of dates to aggregate (overrides target_date if set).
                     Use e.g. [yesterday, day_before] to re-aggregate last 2 days for late events.
                     Dates are processed in sorted order (older first) for deterministic re-aggregation.

    Returns:
        Dict with counts (pandit, search, content, interest) for the last processed date.
    """
    now = timezone.now()
    yesterday = (now - timedelta(days=1)).date()
    if target_dates is not None:
        dates_to_process = sorted(target_dates)
    elif target_date is not None:
        dates_to_process = [target_date]
    else:
        dates_to_process = [yesterday]

    try:
        n_pandit = n_search = n_content = 0
        for d in dates_to_process:
            with transaction.atomic():
                n_pandit += compute_daily_pandit_engagement(d)
            with transaction.atomic():
                n_search += compute_search_trends(d)
            with transaction.atomic():
                compute_user_engagement(d)
            with transaction.atomic():
                n_content += compute_content_interactions(d)
        with transaction.atomic():
            n_interest = update_user_interest_signals()
        logger.info(
            "run_daily_behavior_aggregation dates=%s pandit=%s search=%s content=%s interest_updated=%s",
            dates_to_process, n_pandit, n_search, n_content, n_interest,
        )
        return {"pandit": n_pandit, "search": n_search, "content": n_content, "interest": n_interest}
    except Exception as e:
        logger.exception("run_daily_behavior_aggregation failed: %s", e)
        return {}
