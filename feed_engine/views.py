"""
Phase 17A: Feed API and feed page. Personalized feed for authenticated user.
Visibility controlled by FeatureToggle "news_feed" in Django Admin.
"""
from django.http import JsonResponse, HttpResponseNotFound
from django.shortcuts import render
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

from core.feature_toggle import is_feature_enabled
from feed_engine.services import get_personalized_feed

PER_PAGE = 20
MAX_FETCH = 100


@login_required
@require_GET
def feed_page(request):
    """
    GET /feed/
    Renders the personalized feed page (HTML) with pagination and direct profile links.
    Returns 404 when news_feed feature toggle is disabled.
    """
    if not is_feature_enabled("news_feed"):
        return HttpResponseNotFound()
    feed_items = get_personalized_feed(request.user.id, limit=MAX_FETCH)
    # Enrich pandit items with profile public_id for direct profile links
    from profiles.models import PanditProfile
    pandit_ids = [i["content_id"] for i in feed_items if i.get("content_type") == "pandit"]
    if pandit_ids:
        id_to_public = dict(
            PanditProfile.objects.filter(id__in=pandit_ids).values_list("id", "public_id")
        )
        for item in feed_items:
            if item.get("content_type") == "pandit":
                item["public_id"] = id_to_public.get(item["content_id"])
    paginator = Paginator(feed_items, PER_PAGE)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "feed_engine/feed.html",
        {"page_obj": page_obj},
    )


@login_required
@require_GET
def personalized_feed(request):
    """
    GET /feed/personalized/
    Returns ranked feed items for the current user. Limit query param optional (max 50).
    Returns 404 when news_feed feature toggle is disabled.
    """
    if not is_feature_enabled("news_feed"):
        return HttpResponseNotFound()
    limit = min(int(request.GET.get("limit", 20)), 50)
    results = get_personalized_feed(request.user.id, limit=limit)
    return JsonResponse({"results": results})
