"""
Phase 16: Admin intelligence service. Read-only via BehaviorIntelligenceService where applicable.
DO NOT query UserBehaviorEvent in request paths; use behavior_engine.intelligence_service.
"""
from django.db.models import Count, Sum
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from behavior_engine.intelligence_service import BehaviorIntelligenceService
from behavior_engine.models import (
    UserInterestSignal,
    UserFeedImpression,
    UserInterestAggregate,
)
from search.models import SearchQueryLog
from booking_intent.models import BookingIntent
from reviews.models import Review
from profiles.models import PanditProfile
from accounts.models import User

CACHE_TTL = 120
CACHE_KEYS = {
    "top_pandits": "admin:top_pandits",
    "conversion": "admin:conversion",
    "trending_poojas": "admin:trending_poojas",
    "user_engagement": "admin:user_engagement",
    "platform_growth": "admin:platform_growth",
    "user_interest_distribution": "admin:user_interest_distribution",
    "pandit_engagement_trends": "admin:pandit_engagement_trends",
    "search_trend_intelligence": "admin:search_trend_intelligence",
    "user_engagement_trends": "admin:user_engagement_trends",
    "content_popularity": "admin:content_popularity",
    "user_interest_insights": "admin:user_interest_insights",
    "feed_performance": "admin:feed_performance",
}


class AdminIntelligenceService:
    """Phase 16: Read-only admin intelligence. No writes."""

    @staticmethod
    def get_top_performing_pandits(limit=10):
        """
        Score = profile_views*1 + search_clicks*2 + booking_intents*4 + reviews*1.
        Behavior from aggregated tables via BehaviorIntelligenceService; reviews all-time.
        Returns list of {pandit_id, name, score}.
        """
        limit = min(int(limit), 50)
        cached = cache.get(CACHE_KEYS["top_pandits"])
        if cached is not None:
            return cached[:limit]
        rows = BehaviorIntelligenceService.get_pandit_engagement_scores(days=30)
        scores = {}
        for r in rows:
            pid = r["pandit_id"]
            scores[pid] = (
                (r["profile_views"] or 0) * 1
                + (r["search_clicks"] or 0) * 2
                + (r["booking_intents"] or 0) * 4
            )
        profile_ids = list(scores.keys())
        review_counts = {}
        profile_user_ids = dict(
            PanditProfile.objects.filter(id__in=profile_ids).values_list("id", "user_id")
        )
        if profile_user_ids:
            user_ids = list(profile_user_ids.values())
            for row in (
                Review.objects.filter(
                    pandit_id__in=user_ids, visibility_state=Review.VISIBLE
                )
                .values("pandit_id")
                .annotate(cnt=Count("id"))
            ):
                review_counts[row["pandit_id"]] = row["cnt"]
            for pid, uid in profile_user_ids.items():
                scores[pid] = scores.get(pid, 0) + review_counts.get(uid, 0) * 1
        sorted_ids = sorted(scores.keys(), key=lambda x: -scores[x])[:limit]
        profiles = (
            PanditProfile.objects.filter(
                id__in=sorted_ids, is_profile_approved=True
            )
            .select_related("user")
            .only(
                "id",
                "display_name",
                "user_id",
                "user__id",
                "user__first_name",
                "user__last_name",
                "user__email",
            )
        )
        by_id = {p.id: p.get_display_name() for p in profiles}
        result = [
            {"pandit_id": pid, "name": by_id.get(pid, "—"), "score": scores[pid]}
            for pid in sorted_ids
            if pid in by_id
        ]
        cache.set(CACHE_KEYS["top_pandits"], result, CACHE_TTL)
        return result

    @staticmethod
    def get_booking_conversion_stats():
        """Conversion stats via BehaviorIntelligenceService (cached)."""
        return BehaviorIntelligenceService.get_booking_conversion_stats()

    @staticmethod
    def get_trending_poojas(limit=10):
        """Most searched queries from SearchQueryLog (as trending poojas)."""
        limit = min(int(limit), 50)
        cached = cache.get(CACHE_KEYS["trending_poojas"])
        if cached is not None:
            return cached[:limit]
        rows = list(
            SearchQueryLog.objects.values("query", "search_count")
            .order_by("-search_count")[:limit]
        )
        result = [{"name": r["query"], "count": r["search_count"]} for r in rows]
        cache.set(CACHE_KEYS["trending_poojas"], result, CACHE_TTL)
        return result

    @staticmethod
    def get_user_engagement_metrics():
        """User engagement metrics via BehaviorIntelligenceService (cached)."""
        cached = cache.get(CACHE_KEYS["user_engagement"])
        if cached is not None:
            return cached
        result = BehaviorIntelligenceService.get_user_engagement_metrics()
        cache.set(CACHE_KEYS["user_engagement"], result, CACHE_TTL)
        return result

    @staticmethod
    def get_platform_growth_metrics():
        """
        total_users, total_pandits, total_bookings (intents), total_reviews, weekly growth indicators.
        """
        cached = cache.get(CACHE_KEYS["platform_growth"])
        if cached is not None:
            return cached
        total_users = User.objects.count()
        total_pandits = User.objects.filter(role="pandit").count()
        total_bookings = BookingIntent.objects.count()
        total_reviews = Review.objects.filter(
            visibility_state=Review.VISIBLE
        ).count()
        since_7 = timezone.now() - timedelta(days=7)
        since_14 = timezone.now() - timedelta(days=14)
        bookings_this_week = BookingIntent.objects.filter(
            created_at__gte=since_7
        ).count()
        bookings_prev_week = BookingIntent.objects.filter(
            created_at__gte=since_14, created_at__lt=since_7
        ).count()
        reviews_this_week = Review.objects.filter(
            visibility_state=Review.VISIBLE, created_at__gte=since_7
        ).count()
        reviews_prev_week = Review.objects.filter(
            visibility_state=Review.VISIBLE,
            created_at__gte=since_14,
            created_at__lt=since_7,
        ).count()
        def pct_change(curr, prev):
            if prev == 0:
                return 0.0 if curr == 0 else 100.0
            return round((curr - prev) / prev * 100.0, 2)
        result = {
            "total_users": total_users,
            "total_pandits": total_pandits,
            "total_bookings": total_bookings,
            "total_reviews": total_reviews,
            "bookings_this_week": bookings_this_week,
            "bookings_weekly_growth_pct": pct_change(bookings_this_week, bookings_prev_week),
            "reviews_this_week": reviews_this_week,
            "reviews_weekly_growth_pct": pct_change(reviews_this_week, reviews_prev_week),
        }
        cache.set(CACHE_KEYS["platform_growth"], result, CACHE_TTL)
        return result

    @staticmethod
    def get_user_interest_distribution(limit_per_type=10):
        """
        Aggregate UserInterestSignal by interest_type and interest_value (user_count, total_score).
        Returns e.g. top pooja interests, top city interests, most engaged pandits.
        """
        limit_per_type = min(int(limit_per_type), 30)
        cached = cache.get(CACHE_KEYS["user_interest_distribution"])
        if cached is not None:
            return cached
        out = {
            "pooja_category": [],
            "city": [],
            "pandit": [],
        }
        for interest_type in ("pooja_category", "city", "pandit"):
            rows = (
                UserInterestSignal.objects.filter(interest_type=interest_type)
                .values("interest_value")
                .annotate(user_count=Count("user", distinct=True), total_score=Sum("score"))
                .order_by("-total_score")[:limit_per_type]
            )
            out[interest_type] = [
                {"interest_value": r["interest_value"], "user_count": r["user_count"], "total_score": float(r["total_score"] or 0)}
                for r in rows
            ]
        cache.set(CACHE_KEYS["user_interest_distribution"], out, CACHE_TTL)
        return out

    @staticmethod
    def get_pandit_engagement_trends(limit=20, days=30):
        """From BehaviorIntelligenceService (PanditEngagementDaily)."""
        limit = min(int(limit), 50)
        days = min(int(days), 90)
        cached = cache.get(CACHE_KEYS["pandit_engagement_trends"])
        if cached is not None:
            return cached[:limit]
        result = BehaviorIntelligenceService.get_pandit_engagement_trends(
            limit=limit, days=days
        )
        cache.set(CACHE_KEYS["pandit_engagement_trends"], result, CACHE_TTL)
        return result

    @staticmethod
    def get_search_trend_intelligence(limit=20, days=30):
        """From BehaviorIntelligenceService (SearchTrendDaily)."""
        limit = min(int(limit), 50)
        days = min(int(days), 90)
        cached = cache.get(CACHE_KEYS["search_trend_intelligence"])
        if cached is not None:
            return cached[:limit]
        result = BehaviorIntelligenceService.get_search_trend_intelligence(
            limit=limit, days=days
        )
        cache.set(CACHE_KEYS["search_trend_intelligence"], result, CACHE_TTL)
        return result

    @staticmethod
    def get_user_engagement_trends(days=30):
        """From BehaviorIntelligenceService (UserEngagementDaily)."""
        days = min(int(days), 90)
        cached = cache.get(CACHE_KEYS["user_engagement_trends"])
        if cached is not None:
            return cached
        result = BehaviorIntelligenceService.get_user_engagement_trends(days=days)
        cache.set(CACHE_KEYS["user_engagement_trends"], result, CACHE_TTL)
        return result

    @staticmethod
    def get_content_popularity_metrics(limit=20, days=30):
        """From BehaviorIntelligenceService (ContentInteractionDaily)."""
        limit = min(int(limit), 50)
        days = min(int(days), 90)
        cached = cache.get(CACHE_KEYS["content_popularity"])
        if cached is not None:
            return cached[:limit]
        result = BehaviorIntelligenceService.get_content_popularity_metrics(
            limit=limit, days=days
        )
        cache.set(CACHE_KEYS["content_popularity"], result, CACHE_TTL)
        return result

    @staticmethod
    def get_user_interest_insights(limit_per_type=10):
        """From aggregated UserInterestAggregate (fast). Falls back to UserInterestSignal if empty."""
        limit_per_type = min(int(limit_per_type), 30)
        cached = cache.get(CACHE_KEYS["user_interest_insights"])
        if cached is not None:
            return cached
        out = {"pooja_category": [], "city": [], "pandit": []}
        for interest_type in ("pooja_category", "city", "pandit"):
            rows = (
                UserInterestAggregate.objects.filter(interest_type=interest_type)
                .values("interest_value")
                .annotate(user_count=Count("user", distinct=True), total_score=Sum("score"))
                .order_by("-total_score")[:limit_per_type]
            )
            out[interest_type] = [
                {"interest_value": r["interest_value"], "user_count": r["user_count"], "total_score": float(r["total_score"] or 0)}
                for r in rows
            ]
        if not any(out.values()):
            return AdminIntelligenceService.get_user_interest_distribution(limit_per_type=limit_per_type)
        cache.set(CACHE_KEYS["user_interest_insights"], out, CACHE_TTL)
        return out

    @staticmethod
    def get_feed_performance_metrics():
        """Feed analytics from UserFeedImpression: impressions, clicks, engagement rate."""
        cached = cache.get(CACHE_KEYS["feed_performance"])
        if cached is not None:
            return cached
        total_impressions = UserFeedImpression.objects.count()
        feed_clicks = UserFeedImpression.objects.filter(was_clicked=True).count()
        engagement_rate = (feed_clicks / total_impressions) if total_impressions else 0.0
        result = {
            "feed_impressions": total_impressions,
            "feed_clicks": feed_clicks,
            "feed_engagement_rate": round(engagement_rate, 4),
        }
        cache.set(CACHE_KEYS["feed_performance"], result, CACHE_TTL)
        return result
