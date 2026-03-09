"""
Phase 13: Admin analytics service. Read-only queries on existing tables.
Phase 13.1: Short-lived caching to reduce DB load; response structure unchanged.
Phase 13.1.1: Cache versioning and safe invalidation (clear_analytics_cache).
"""
from django.db.models import Count, Sum
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta

from search.models import SearchQueryLog, SearchResultClick
from reviews.models import Review
from profiles.models import PanditProfile
from booking_intent.models import BookingIntent
from masterdata.models import City
from django.contrib.auth import get_user_model

User = get_user_model()

# Phase 13.1: Cache keys and TTLs (seconds)
TRENDING_SEARCHES_CACHE_KEY = "analytics:trending_searches"
TOP_CLICKED_PANDITS_CACHE_KEY = "analytics:top_clicked_pandits"
TOP_REVIEWED_PANDITS_CACHE_KEY = "analytics:top_reviewed_pandits"
CITY_ACTIVITY_CACHE_KEY = "analytics:city_activity"
BOOKING_STATS_CACHE_KEY = "analytics:booking_stats"
USER_ENGAGEMENT_CACHE_KEY = "analytics:user_engagement"

TRENDING_SEARCHES_CACHE_TTL = 60
TOP_CLICKED_PANDITS_CACHE_TTL = 60
TOP_REVIEWED_PANDITS_CACHE_TTL = 60
CITY_ACTIVITY_CACHE_TTL = 120
BOOKING_STATS_CACHE_TTL = 60
USER_ENGAGEMENT_CACHE_TTL = 60

# Phase 13.1.1: Increment to invalidate all analytics caches when logic changes
ANALYTICS_CACHE_VERSION = 1


class AdminAnalyticsService:
    """Read-only analytics for administrators. All data from existing tables."""

    @staticmethod
    def get_trending_searches(limit=10):
        """Top searched queries from SearchQueryLog. Cached 60s; safe empty result."""
        cached = cache.get(TRENDING_SEARCHES_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
        if cached is not None:
            return cached
        rows = list(
            SearchQueryLog.objects
            .values("query", "search_count")
            .order_by("-search_count")[:limit]
        )
        results = [] if not rows else [{"query": r["query"], "count": r["search_count"]} for r in rows]
        cache.set(TRENDING_SEARCHES_CACHE_KEY, results, TRENDING_SEARCHES_CACHE_TTL, version=ANALYTICS_CACHE_VERSION)
        return results

    @staticmethod
    def get_top_clicked_pandits(limit=10):
        """Most clicked pandits from SearchResultClick. Cached 60s; safe empty result."""
        cached = cache.get(TOP_CLICKED_PANDITS_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
        if cached is not None:
            return cached
        rows = list(
            SearchResultClick.objects
            .values("pandit")
            .annotate(clicks=Count("id"))
            .order_by("-clicks")[:limit]
        )
        if not rows:
            results = []
        else:
            pandit_ids = [r["pandit"] for r in rows]
            profiles = PanditProfile.objects.filter(id__in=pandit_ids).select_related("user").only("id", "display_name", "user_id")
            by_id = {p.id: p.get_display_name() for p in profiles}
            click_by_id = {r["pandit"]: r["clicks"] for r in rows}
            results = [
                {"pandit_name": by_id.get(pid, "—"), "clicks": click_by_id[pid]}
                for pid in pandit_ids
            ]
        cache.set(TOP_CLICKED_PANDITS_CACHE_KEY, results, TOP_CLICKED_PANDITS_CACHE_TTL, version=ANALYTICS_CACHE_VERSION)
        return results

    @staticmethod
    def get_top_reviewed_pandits(limit=10):
        """Most reviewed pandits from Review (pandit = User). Cached 60s; safe empty result."""
        cached = cache.get(TOP_REVIEWED_PANDITS_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
        if cached is not None:
            return cached
        rows = list(
            Review.objects
            .values("pandit")
            .annotate(review_count=Count("id"))
            .order_by("-review_count")[:limit]
        )
        if not rows:
            results = []
        else:
            user_ids = [r["pandit"] for r in rows]
            profiles = PanditProfile.objects.filter(user_id__in=user_ids).select_related("user").only("id", "user_id", "display_name")
            by_user_id = {p.user_id: p.get_display_name() for p in profiles}
            review_by_uid = {r["pandit"]: r["review_count"] for r in rows}
            results = [
                {
                    "pandit_name": by_user_id.get(uid, "—"),
                    "review_count": review_by_uid[uid],
                }
                for uid in user_ids
            ]
        cache.set(TOP_REVIEWED_PANDITS_CACHE_KEY, results, TOP_REVIEWED_PANDITS_CACHE_TTL, version=ANALYTICS_CACHE_VERSION)
        return results

    @staticmethod
    def get_city_activity(limit=10):
        """Most active cities by number of pandits (M2M). Cached 120s; safe empty result."""
        cached = cache.get(CITY_ACTIVITY_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
        if cached is not None:
            return cached
        rows = list(
            City.objects.filter(is_active=True)
            .annotate(pandits=Count("pandits"))
            .filter(pandits__gt=0)
            .values("name", "pandits")
            .order_by("-pandits")[:limit]
        )
        results = [] if not rows else [{"city": r["name"], "pandits": r["pandits"]} for r in rows]
        cache.set(CITY_ACTIVITY_CACHE_KEY, results, CITY_ACTIVITY_CACHE_TTL, version=ANALYTICS_CACHE_VERSION)
        return results

    @staticmethod
    def get_booking_stats():
        """Booking intent stats: total, this week, this month. Cached 60s; safe count (never None)."""
        cached = cache.get(BOOKING_STATS_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
        if cached is not None:
            return cached
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        total = BookingIntent.objects.count() or 0
        this_week = BookingIntent.objects.filter(created_at__gte=week_ago).count() or 0
        this_month = BookingIntent.objects.filter(created_at__gte=month_ago).count() or 0
        stats = {
            "total_booking_requests": total,
            "requests_this_week": this_week,
            "requests_this_month": this_month,
        }
        cache.set(BOOKING_STATS_CACHE_KEY, stats, BOOKING_STATS_CACHE_TTL, version=ANALYTICS_CACHE_VERSION)
        return stats

    @staticmethod
    def get_user_engagement():
        """Platform engagement: total users, pandits, reviews, searches, clicks. Cached 60s; safe counts."""
        cached = cache.get(USER_ENGAGEMENT_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
        if cached is not None:
            return cached
        total_users = User.objects.count() or 0
        total_pandits = PanditProfile.objects.filter(is_profile_approved=True).count() or 0
        total_reviews = Review.objects.count() or 0
        total_searches = SearchQueryLog.objects.aggregate(total=Sum("search_count"))["total"] or 0
        total_clicks = SearchResultClick.objects.count() or 0
        metrics = {
            "total_users": total_users,
            "total_pandits": total_pandits,
            "total_reviews": total_reviews,
            "total_search_queries": total_searches,
            "total_clicks": total_clicks,
        }
        cache.set(USER_ENGAGEMENT_CACHE_KEY, metrics, USER_ENGAGEMENT_CACHE_TTL, version=ANALYTICS_CACHE_VERSION)
        return metrics


def clear_analytics_cache():
    """Phase 13.1.1: Clear all analytics caches (manual use only). Increment ANALYTICS_CACHE_VERSION to invalidate on deploy."""
    cache.delete(TRENDING_SEARCHES_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
    cache.delete(TOP_CLICKED_PANDITS_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
    cache.delete(TOP_REVIEWED_PANDITS_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
    cache.delete(CITY_ACTIVITY_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
    cache.delete(BOOKING_STATS_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
    cache.delete(USER_ENGAGEMENT_CACHE_KEY, version=ANALYTICS_CACHE_VERSION)
