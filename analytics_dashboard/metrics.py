"""
Phase 13: Optional metrics aggregation. Combines multiple analytics signals.
Read-only; no schema changes.
"""
from .services import AdminAnalyticsService


def get_platform_summary():
    """Return combined platform summary: total users, pandits, reviews, searches, clicks."""
    engagement = AdminAnalyticsService.get_user_engagement()
    return {
        "total_users": engagement["total_users"],
        "total_pandits": engagement["total_pandits"],
        "total_reviews": engagement["total_reviews"],
        "total_searches": engagement["total_search_queries"],
        "total_clicks": engagement["total_clicks"],
    }
