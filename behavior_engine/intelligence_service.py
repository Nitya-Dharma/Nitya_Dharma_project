"""
Behavioral Intelligence Service — single gateway for reading behavioral intelligence.

All production systems (recommendations, feed, admin dashboards) should read from
this service instead of querying raw event tables or aggregate tables directly.

GUARDRAIL: DO NOT query UserBehaviorEvent or UserContentInteraction in request/response
paths outside this module. Only batch jobs (aggregation_services, interest_scoring)
may query raw event tables.
"""
import logging
from django.utils import timezone
from django.db.models import Sum
from django.core.cache import cache
from datetime import timedelta

from .models import (
    UserBehaviorEvent,
    PanditEngagementDaily,
    SearchTrendDaily,
    UserEngagementDaily,
    ContentInteractionDaily,
    EVENT_PANDIT_PROFILE_VIEW,
    EVENT_BOOKING_INTENT_SENT,
)

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes
LOCK_TIMEOUT = 10  # seconds for soft lock (stampede prevention)
BEHAVIOR_INTEL_CACHE_VERSION = "v1"
MAX_QUERY_LIMIT = 1000  # safe cap for list-returning intelligence queries


def _cache_key(prefix):
    return f"behavior_intel_{BEHAVIOR_INTEL_CACHE_VERSION}_{prefix}"


class BehaviorIntelligenceService:
    """
    Unified read-only interface for behavioral intelligence from aggregated tables.
    Uses caching to reduce load. Request-path code should use this instead of raw events.
    """

    @staticmethod
    def get_pandit_engagement_scores(days=30):
        """
        Pandit engagement from PanditEngagementDaily (aggregated).
        Returns list of dicts: pandit_id, profile_views, search_clicks, booking_intents, engagement_score (summed).
        """
        cache_key = _cache_key(f"pandit_engagement_{days}")
        cached = cache.get(cache_key)
        logger.debug(
            "BehaviorIntelligenceService.get_pandit_engagement_scores cache_hit=%s",
            cached is not None,
        )
        if cached is not None:
            return cached
        lock_key = cache_key + "_lock"
        # Acquire short-lived cache lock.
        # Lock is always released in finally to avoid deadlocks.
        if not cache.add(lock_key, True, timeout=LOCK_TIMEOUT):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            return []
        try:
            since = timezone.now().date() - timedelta(days=days)
            rows = (
                PanditEngagementDaily.objects.filter(date__gte=since)
                .values("pandit_id")
                .annotate(
                    profile_views=Sum("profile_views"),
                    search_clicks=Sum("search_clicks"),
                    booking_intents=Sum("booking_intents"),
                    engagement_score=Sum("engagement_score"),
                )
                .order_by("-engagement_score")[:MAX_QUERY_LIMIT]
            )
            result = [
                {
                    "pandit_id": r["pandit_id"],
                    "profile_views": r["profile_views"] or 0,
                    "search_clicks": r["search_clicks"] or 0,
                    "booking_intents": r["booking_intents"] or 0,
                    "engagement_score": float(r["engagement_score"] or 0),
                }
                for r in rows
            ]
            cache.set(cache_key, result, CACHE_TTL)
            return result
        finally:
            cache.delete(lock_key)

    @staticmethod
    def get_trending_searches(days=7, limit=20):
        """Trending search queries from SearchTrendDaily (aggregated)."""
        cache_key = _cache_key(f"trending_searches_{days}_{limit}")
        cached = cache.get(cache_key)
        logger.debug(
            "BehaviorIntelligenceService.get_trending_searches cache_hit=%s",
            cached is not None,
        )
        if cached is not None:
            return cached
        lock_key = cache_key + "_lock"
        # Acquire short-lived cache lock.
        # Lock is always released in finally to avoid deadlocks.
        if not cache.add(lock_key, True, timeout=LOCK_TIMEOUT):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            return []
        try:
            since = timezone.now().date() - timedelta(days=days)
            limit = min(limit, MAX_QUERY_LIMIT)
            rows = (
                SearchTrendDaily.objects.filter(date__gte=since)
                .values("query")
                .annotate(total=Sum("search_count"))
                .order_by("-total")[:limit]
            )
            result = [{"query": r["query"], "total": r["total"] or 0} for r in rows]
            cache.set(cache_key, result, CACHE_TTL)
            return result
        finally:
            cache.delete(lock_key)

    @staticmethod
    def get_content_popularity(days=7, content_type=None):
        """
        Content popularity from ContentInteractionDaily (aggregated).
        Returns list of dicts: content_type, content_id, score (sum of clicks).
        """
        cache_key = _cache_key(f"content_popularity_{days}_{content_type or 'all'}")
        cached = cache.get(cache_key)
        logger.debug(
            "BehaviorIntelligenceService.get_content_popularity cache_hit=%s",
            cached is not None,
        )
        if cached is not None:
            return cached
        lock_key = cache_key + "_lock"
        # Acquire short-lived cache lock.
        # Lock is always released in finally to avoid deadlocks.
        if not cache.add(lock_key, True, timeout=LOCK_TIMEOUT):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            return []
        try:
            since = timezone.now().date() - timedelta(days=days)
            qs = ContentInteractionDaily.objects.filter(date__gte=since)
            if content_type:
                qs = qs.filter(content_type=content_type)
            rows = (
                qs.values("content_type", "content_id")
                .annotate(score=Sum("clicks"))
                .order_by("-score")[:MAX_QUERY_LIMIT]
            )
            result = [
                {"content_type": r["content_type"], "content_id": r["content_id"], "score": r["score"] or 0}
                for r in rows
            ]
            cache.set(cache_key, result, CACHE_TTL)
            return result
        finally:
            cache.delete(lock_key)

    @staticmethod
    def get_engagement_and_popularity_for_feed(days=7, pandit_ids=None):
        """
        Engagement (PanditEngagementDaily) and popularity (ContentInteractionDaily) for feed precompute.
        Returns (engagement_by_id: dict, popularity_by_id: dict) for given pandit_ids.
        """
        if not pandit_ids:
            return {}, {}
        since = timezone.now().date() - timedelta(days=days)
        engagement_qs = (
            PanditEngagementDaily.objects.filter(date__gte=since, pandit_id__in=pandit_ids)
            .values("pandit_id")
            .annotate(total=Sum("engagement_score"))
        )
        engagement_by_id = {r["pandit_id"]: float(r["total"] or 0) for r in engagement_qs}

        popularity_qs = (
            ContentInteractionDaily.objects.filter(
                date__gte=since,
                content_type="pandit_profile",
                content_id__in=pandit_ids,
            )
            .values("content_id")
            .annotate(
                total_clicks=Sum("clicks"),
                total_impressions=Sum("impressions"),
            )
        )
        popularity_by_id = {}
        for r in popularity_qs:
            cid = r["content_id"]
            popularity_by_id[cid] = float((r["total_clicks"] or 0) + (r["total_impressions"] or 0))

        return engagement_by_id, popularity_by_id

    @staticmethod
    def get_recently_viewed_pandit_ids(user_id, limit=5):
        """
        Last viewed pandit profile IDs for this user (most recent first, unique).
        EXCEPTION: This is the only request-path read from UserBehaviorEvent, because
        recency per user is not stored in aggregate tables.
        """
        rows = (
            UserBehaviorEvent.objects.filter(
                event_type=EVENT_PANDIT_PROFILE_VIEW,
                user_id=user_id,
                object_type="pandit_profile",
                object_id__isnull=False,
            )
            .order_by("-created_at")
            .values_list("object_id", flat=True)[: limit * 3]
        )
        seen = set()
        profile_ids = []
        for pid in rows:
            if pid not in seen:
                seen.add(pid)
                profile_ids.append(pid)
            if len(profile_ids) >= limit:
                break
        return profile_ids

    @staticmethod
    def get_booking_conversion_stats():
        """
        Platform-level profile_views and booking_intents for conversion rate.
        Uses UserBehaviorEvent (no aggregate table for platform-level conversion yet). Cached.
        """
        cache_key = _cache_key("booking_conversion")
        cached = cache.get(cache_key)
        logger.debug(
            "BehaviorIntelligenceService.get_booking_conversion_stats cache_hit=%s",
            cached is not None,
        )
        if cached is not None:
            return cached
        lock_key = cache_key + "_lock"
        # Acquire short-lived cache lock.
        # Lock is always released in finally to avoid deadlocks.
        if not cache.add(lock_key, True, timeout=LOCK_TIMEOUT):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            return {"profile_views": 0, "booking_intents": 0, "conversion_rate": 0.0}
        try:
            profile_views = UserBehaviorEvent.objects.filter(
                event_type=EVENT_PANDIT_PROFILE_VIEW
            ).count()
            booking_intents = UserBehaviorEvent.objects.filter(
                event_type=EVENT_BOOKING_INTENT_SENT
            ).count()
            conversion_rate = (booking_intents / profile_views) if profile_views else 0.0
            result = {
                "profile_views": profile_views,
                "booking_intents": booking_intents,
                "conversion_rate": round(conversion_rate, 4),
            }
            cache.set(cache_key, result, CACHE_TTL)
            return result
        finally:
            cache.delete(lock_key)

    @staticmethod
    def get_user_engagement_metrics():
        """
        Platform engagement: total_page_views, total_search_queries, avg_events_per_user,
        active_users_last_7_days. Uses UserEngagementDaily where possible; falls back to
        UserBehaviorEvent for metrics not in aggregates.
        """
        cache_key = _cache_key("user_engagement_metrics")
        cached = cache.get(cache_key)
        logger.debug(
            "BehaviorIntelligenceService.get_user_engagement_metrics cache_hit=%s",
            cached is not None,
        )
        if cached is not None:
            return cached
        lock_key = cache_key + "_lock"
        default = {
            "total_page_views": 0,
            "total_search_queries": 0,
            "avg_events_per_user": 0.0,
            "active_users_last_7_days": 0,
        }
        # Acquire short-lived cache lock.
        # Lock is always released in finally to avoid deadlocks.
        if not cache.add(lock_key, True, timeout=LOCK_TIMEOUT):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            return default
        try:
            since_30 = timezone.now().date() - timedelta(days=30)
            since_7 = timezone.now() - timedelta(days=7)

            # From aggregates
            daily_rows = UserEngagementDaily.objects.filter(date__gte=since_30).aggregate(
                total_page_views=Sum("total_page_views"),
                total_searches=Sum("total_searches"),
            )
            total_page_views = (daily_rows.get("total_page_views") or 0) or 0
            total_search_queries = (daily_rows.get("total_searches") or 0) or 0

            # active_users_7d and total_events / distinct users: from raw
            total_events = UserBehaviorEvent.objects.count()
            distinct_users = (
                UserBehaviorEvent.objects.filter(user_id__isnull=False)
                .values("user_id")
                .distinct()
                .count()
            )
            avg_events_per_user = (total_events / distinct_users) if distinct_users else 0.0
            active_7d = (
                UserBehaviorEvent.objects.filter(created_at__gte=since_7, user_id__isnull=False)
                .values("user_id")
                .distinct()
                .count()
            )

            result = {
                "total_page_views": total_page_views,
                "total_search_queries": total_search_queries,
                "avg_events_per_user": round(avg_events_per_user, 2),
                "active_users_last_7_days": active_7d,
            }
            cache.set(cache_key, result, CACHE_TTL)
            return result
        finally:
            cache.delete(lock_key)

    @staticmethod
    def get_pandit_engagement_trends(limit=20, days=30):
        """From PanditEngagementDaily. For admin dashboard."""
        limit = min(limit, MAX_QUERY_LIMIT)
        cache_key = _cache_key(f"pandit_engagement_trends_{limit}_{days}")
        cached = cache.get(cache_key)
        logger.debug(
            "BehaviorIntelligenceService.get_pandit_engagement_trends cache_hit=%s",
            cached is not None,
        )
        if cached is not None:
            return cached
        lock_key = cache_key + "_lock"
        # Acquire short-lived cache lock.
        # Lock is always released in finally to avoid deadlocks.
        if not cache.add(lock_key, True, timeout=LOCK_TIMEOUT):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            return []
        try:
            since = timezone.now().date() - timedelta(days=days)
            rows = (
                PanditEngagementDaily.objects.filter(date__gte=since)
                .values("pandit_id")
                .annotate(
                    profile_views=Sum("profile_views"),
                    search_clicks=Sum("search_clicks"),
                    booking_intents=Sum("booking_intents"),
                    engagement_score=Sum("engagement_score"),
                )
                .order_by("-engagement_score")[:limit]
            )
            result = [
                {
                    "pandit_id": r["pandit_id"],
                    "profile_views": r["profile_views"] or 0,
                    "search_clicks": r["search_clicks"] or 0,
                    "booking_intents": r["booking_intents"] or 0,
                    "engagement_score": float(r["engagement_score"] or 0),
                }
                for r in rows
            ]
            cache.set(cache_key, result, CACHE_TTL)
            return result
        finally:
            cache.delete(lock_key)

    @staticmethod
    def get_search_trend_intelligence(limit=20, days=30):
        """From SearchTrendDaily. For admin dashboard."""
        limit = min(limit, MAX_QUERY_LIMIT)
        cache_key = _cache_key(f"search_trend_{limit}_{days}")
        cached = cache.get(cache_key)
        logger.debug(
            "BehaviorIntelligenceService.get_search_trend_intelligence cache_hit=%s",
            cached is not None,
        )
        if cached is not None:
            return cached
        lock_key = cache_key + "_lock"
        # Acquire short-lived cache lock.
        # Lock is always released in finally to avoid deadlocks.
        if not cache.add(lock_key, True, timeout=LOCK_TIMEOUT):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            return []
        try:
            since = timezone.now().date() - timedelta(days=days)
            rows = (
                SearchTrendDaily.objects.filter(date__gte=since)
                .values("query")
                .annotate(
                    search_count=Sum("search_count"),
                    click_count=Sum("click_count"),
                    conversion_count=Sum("conversion_count"),
                )
                .order_by("-search_count")[:limit]
            )
            result = [
                {
                    "query": r["query"],
                    "search_count": r["search_count"] or 0,
                    "click_count": r["click_count"] or 0,
                    "conversion_count": r["conversion_count"] or 0,
                }
                for r in rows
            ]
            cache.set(cache_key, result, CACHE_TTL)
            return result
        finally:
            cache.delete(lock_key)

    @staticmethod
    def get_user_engagement_trends(days=30):
        """From UserEngagementDaily. For admin dashboard."""
        days = min(days, MAX_QUERY_LIMIT)
        cache_key = _cache_key(f"user_engagement_trends_{days}")
        cached = cache.get(cache_key)
        logger.debug(
            "BehaviorIntelligenceService.get_user_engagement_trends cache_hit=%s",
            cached is not None,
        )
        if cached is not None:
            return cached
        lock_key = cache_key + "_lock"
        # Acquire short-lived cache lock.
        # Lock is always released in finally to avoid deadlocks.
        if not cache.add(lock_key, True, timeout=LOCK_TIMEOUT):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            return []
        try:
            since = timezone.now().date() - timedelta(days=days)
            rows = list(
                UserEngagementDaily.objects.filter(date__gte=since).order_by("-date")[:days]
            )
            result = [
                {
                    "date": str(r.date),
                    "active_users": r.active_users,
                    "total_sessions": r.total_sessions,
                    "total_page_views": r.total_page_views,
                    "total_searches": r.total_searches,
                    "total_interactions": r.total_interactions,
                    "avg_session_duration_ms": r.avg_session_duration_ms,
                }
                for r in rows
            ]
            cache.set(cache_key, result, CACHE_TTL)
            return result
        finally:
            cache.delete(lock_key)

    @staticmethod
    def get_content_popularity_metrics(limit=20, days=30):
        """From ContentInteractionDaily. For admin dashboard."""
        limit = min(limit, MAX_QUERY_LIMIT)
        cache_key = _cache_key(f"content_popularity_metrics_{limit}_{days}")
        cached = cache.get(cache_key)
        logger.debug(
            "BehaviorIntelligenceService.get_content_popularity_metrics cache_hit=%s",
            cached is not None,
        )
        if cached is not None:
            return cached
        lock_key = cache_key + "_lock"
        # Acquire short-lived cache lock.
        # Lock is always released in finally to avoid deadlocks.
        if not cache.add(lock_key, True, timeout=LOCK_TIMEOUT):
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            return []
        try:
            since = timezone.now().date() - timedelta(days=days)
            rows = (
                ContentInteractionDaily.objects.filter(date__gte=since)
                .values("content_type", "content_id")
                .annotate(
                    impressions=Sum("impressions"),
                    clicks=Sum("clicks"),
                    saves=Sum("saves"),
                    shares=Sum("shares"),
                )
                .order_by("-clicks")[:limit]
            )
            result = [
                {
                    "content_type": r["content_type"],
                    "content_id": r["content_id"],
                    "impressions": r["impressions"] or 0,
                    "clicks": r["clicks"] or 0,
                    "saves": r["saves"] or 0,
                    "shares": r["shares"] or 0,
                }
                for r in rows
            ]
            cache.set(cache_key, result, CACHE_TTL)
            return result
        finally:
            cache.delete(lock_key)
