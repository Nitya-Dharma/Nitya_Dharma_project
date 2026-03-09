"""
Phase 17A: Feed generation service. Uses ranking engine; caches result.
"""
from django.core.cache import cache

from feed_engine.ranking import FeedRankingEngine


CACHE_TTL = 60
FEED_CACHE_VERSION = "v1"


def get_personalized_feed(user_id, limit=20):
    """
    Return personalized feed for user: fetch candidates, rank, return top limit.
    Cached 60 seconds per user (key includes version and limit for safe invalidation).
    """
    cache_key = f"user_feed_{FEED_CACHE_VERSION}_{user_id}_{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    results = FeedRankingEngine.generate_user_feed(user_id, limit=limit)
    cache.set(cache_key, results, CACHE_TTL)
    return results
