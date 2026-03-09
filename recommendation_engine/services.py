"""
Phase 15: Recommendation service. Read-only; uses existing tables only.
"""
from django.core.cache import cache
from django.db.models import Q

from recommendation_engine.algorithms import compute_trending_pandits
from behavior_engine.intelligence_service import BehaviorIntelligenceService
from search.models import SearchQueryLog
from profiles.models import PanditProfile

CACHE_TTL = 60
CACHE_KEY_TRENDING_PANDITS = "recommendation:trending_pandits"
CACHE_KEY_POPULAR_POOJAS = "recommendation:popular_poojas"
CACHE_KEY_TRENDING_SEARCHES = "recommendation:trending_searches"


def _pandit_list_items(profile_ids):
    """Resolve profile ids to list of {pandit_id, name}. Only approved."""
    if not profile_ids:
        return []
    profiles = PanditProfile.objects.filter(
        id__in=profile_ids,
        is_profile_approved=True,
    ).select_related("user")
    by_id = {p.id: p.get_display_name() for p in profiles}
    order = [pid for pid in profile_ids if pid in by_id]
    return [{"pandit_id": pid, "name": by_id[pid]} for pid in order]


class RecommendationService:
    """Phase 15: Behavior-driven suggestions. Read-only."""

    @staticmethod
    def get_trending_pandits(limit=10):
        cached = cache.get(CACHE_KEY_TRENDING_PANDITS)
        if cached is not None:
            return cached[:limit]
        pairs = compute_trending_pandits(limit=limit)
        profile_ids = [p[0] for p in pairs]
        result = _pandit_list_items(profile_ids)
        cache.set(CACHE_KEY_TRENDING_PANDITS, result, CACHE_TTL)
        return result

    @staticmethod
    def get_popular_poojas(limit=10):
        """Most frequent search queries (pooja-related). From SearchQueryLog."""
        cached = cache.get(CACHE_KEY_POPULAR_POOJAS)
        if cached is not None:
            return cached[:limit]
        rows = list(
            SearchQueryLog.objects.values("query", "search_count")
            .order_by("-search_count")[:limit]
        )
        result = [{"name": r["query"], "count": r["search_count"]} for r in rows]
        cache.set(CACHE_KEY_POPULAR_POOJAS, result, CACHE_TTL)
        return result

    @staticmethod
    def get_recently_viewed_pandits(user, limit=5):
        """Last pandit_profile_view events for this user, unique pandits (via intelligence service)."""
        if not user or not user.is_authenticated:
            return []
        profile_ids = BehaviorIntelligenceService.get_recently_viewed_pandit_ids(
            user.id, limit=limit
        )
        return _pandit_list_items(profile_ids)

    @staticmethod
    def get_similar_pandits(pandit_id, limit=5):
        """Same city and pooja as given pandit; exclude self. Approved only."""
        try:
            profile = PanditProfile.objects.get(id=pandit_id, is_profile_approved=True)
        except PanditProfile.DoesNotExist:
            return []
        city_ids = list(profile.cities_served.filter(is_active=True).values_list("id", flat=True))
        pooja_ids = list(profile.poojas_performed.values_list("id", flat=True))
        if not city_ids and not pooja_ids:
            return []
        base = Q(is_profile_approved=True) & ~Q(id=pandit_id)
        city_q = Q(cities_served__in=city_ids) if city_ids else Q()
        pooja_q = Q(poojas_performed__in=pooja_ids) if pooja_ids else Q()
        combined = (city_q | pooja_q) if (city_q and pooja_q) else (city_q or pooja_q)
        similar = (
            PanditProfile.objects.filter(base & combined)
            .distinct()
            .values_list("id", flat=True)[:limit]
        )
        return _pandit_list_items(list(similar))

    @staticmethod
    def get_trending_searches(limit=10):
        cached = cache.get(CACHE_KEY_TRENDING_SEARCHES)
        if cached is not None:
            return cached[:limit]
        rows = list(
            SearchQueryLog.objects.values("query", "search_count")
            .order_by("-search_count")[:limit]
        )
        result = [{"query": r["query"], "count": r["search_count"]} for r in rows]
        cache.set(CACHE_KEY_TRENDING_SEARCHES, result, CACHE_TTL)
        return result
