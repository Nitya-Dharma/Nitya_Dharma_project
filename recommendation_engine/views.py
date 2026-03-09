"""
Phase 15: Read-only recommendation API. No auth required for public endpoints;
recently-viewed returns empty for anonymous users.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_page

from recommendation_engine.services import RecommendationService


@require_GET
@cache_page(60)
def trending_pandits(request):
    limit = min(int(request.GET.get("limit", 10)), 50)
    data = RecommendationService.get_trending_pandits(limit=limit)
    return JsonResponse({"results": data})


@require_GET
@cache_page(60)
def popular_poojas(request):
    limit = min(int(request.GET.get("limit", 10)), 50)
    data = RecommendationService.get_popular_poojas(limit=limit)
    return JsonResponse({"results": data})


@require_GET
@cache_page(60)
def trending_searches(request):
    limit = min(int(request.GET.get("limit", 10)), 50)
    data = RecommendationService.get_trending_searches(limit=limit)
    return JsonResponse({"results": data})


@require_GET
def similar_pandits(request, pandit_id):
    limit = min(int(request.GET.get("limit", 5)), 20)
    data = RecommendationService.get_similar_pandits(pandit_id=pandit_id, limit=limit)
    return JsonResponse({"results": data})


@require_GET
def recently_viewed(request):
    """Returns empty list for anonymous users."""
    limit = min(int(request.GET.get("limit", 5)), 20)
    data = RecommendationService.get_recently_viewed_pandits(user=request.user, limit=limit)
    return JsonResponse({"results": data})
