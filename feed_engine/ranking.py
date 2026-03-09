"""
Phase 17A: Feed ranking engine. Combines interest, engagement, popularity, freshness.
final_score = interest*0.40 + engagement*0.25 + popularity*0.20 + freshness*0.15
"""

from django.core.cache import cache

from feed_engine.models import FeedItemCandidate
from behavior_engine.models import UserInterestSignal, PanditEngagementDaily, ContentInteractionDaily
from django.utils import timezone
from datetime import timedelta


# Weights for final score (must sum to 1.0)
WEIGHT_INTEREST = 0.40
WEIGHT_ENGAGEMENT = 0.25
WEIGHT_POPULARITY = 0.20
WEIGHT_FRESHNESS = 0.15
MAX_CANDIDATES = 200


def _normalize(x, low=0, high=1):
    """Clamp to [0, 1] or normalize; avoid div by zero."""
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (float(x) - low) / (high - low)))


class FeedRankingEngine:
    """
    Ranks feed candidates using user interest vector and precomputed scores.
    Does not modify search or recommendation logic.
    """

    @staticmethod
    def _get_user_interest_vector(user_id):
        """Return dict (interest_type, interest_value) -> score, normalized to 0-1 scale for matching."""
        rows = UserInterestSignal.objects.filter(user_id=user_id).values("interest_type", "interest_value", "score")
        if not rows:
            return {}
        scores = [r["score"] for r in rows]
        max_s = max(scores) or 1
        return {
            (r["interest_type"], r["interest_value"]): _normalize(r["score"], 0, max_s)
            for r in rows
        }

    @staticmethod
    def _get_user_interest_vector_raw(user_id):
        """Return dict (interest_type, interest_value) -> raw score. Cached 10 min to reduce DB reads."""
        CACHE_TTL = 600  # 10 minutes
        cache_key = f"user_interest_vector_{user_id}"
        cached_vector = cache.get(cache_key)
        if cached_vector is not None:
            return cached_vector
        rows = (
            UserInterestSignal.objects.filter(user_id=user_id).values("interest_type", "interest_value", "score")
        )
        vector = {
            (row["interest_type"], str(row["interest_value"])): float(row["score"] or 0)
            for row in rows
        }
        cache.set(cache_key, vector, CACHE_TTL)
        return vector

    @staticmethod
    def _interest_raw_for_item(content_type, content_id, raw_vector):
        """Match content to user interest; return raw score. pandit/42 -> (pandit, '42'); etc."""
        key_pandit = ("pandit", str(content_id))
        if key_pandit in raw_vector:
            return raw_vector[key_pandit]
        key_pooja = ("pooja_category", str(content_id))
        if key_pooja in raw_vector:
            return raw_vector[key_pooja]
        key_city = ("city", str(content_id))
        if key_city in raw_vector:
            return raw_vector[key_city]
        return 0.0

    @staticmethod
    def _interest_score_for_item(content_type, content_id, interest_vector):
        """Match content to user interest. pandit/42 -> (pandit, '42'); pooja_category -> (pooja_category, value)."""
        key_pandit = ("pandit", str(content_id))
        if key_pandit in interest_vector:
            return interest_vector[key_pandit]
        key_pooja = ("pooja_category", str(content_id))
        if key_pooja in interest_vector:
            return interest_vector[key_pooja]
        key_city = ("city", str(content_id))
        if key_city in interest_vector:
            return interest_vector[key_city]
        return 0.0

    @staticmethod
    def generate_user_feed(user_id, limit=20):
        """
        Fetch up to MAX_CANDIDATES candidates, score with interest + engagement + popularity + freshness, return top limit.
        Returns list of {"content_type": str, "content_id": int, "score": float}.
        """
        candidates = list(FeedItemCandidate.objects.all()[:MAX_CANDIDATES])
        if not candidates:
            return []

        raw_interest_vector = FeedRankingEngine._get_user_interest_vector_raw(user_id)
        engagement_max = max((c.engagement_score for c in candidates), default=1) or 1
        popularity_max = max((c.popularity_score for c in candidates), default=1) or 1
        freshness_max = max((c.freshness_score for c in candidates), default=1) or 1

        scored = []
        for c in candidates:
            raw_interest = FeedRankingEngine._interest_raw_for_item(c.content_type, c.content_id, raw_interest_vector)
            interest_score = min(raw_interest / 20.0, 1.0)
            eng_n = _normalize(c.engagement_score, 0, engagement_max)
            pop_n = _normalize(c.popularity_score, 0, popularity_max)
            fresh_n = _normalize(c.freshness_score, 0, freshness_max)
            final = (
                WEIGHT_INTEREST * interest_score
                + WEIGHT_ENGAGEMENT * eng_n
                + WEIGHT_POPULARITY * pop_n
                + WEIGHT_FRESHNESS * fresh_n
            )
            scored.append({"content_type": c.content_type, "content_id": c.content_id, "score": round(final, 4)})

        scored.sort(key=lambda x: -x["score"])
        return scored[:limit]
