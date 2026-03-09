"""
Phase 16: Admin intelligence API views. Read-only; staff-only.
"""
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_page

from admin_intelligence.services import AdminIntelligenceService
from behavior_engine.data_validation import validate_behavior_aggregates


@staff_member_required
def dashboard_page(request):
    """Renders the Intelligence Dashboard page (calls services server-side)."""
    aggregate_issues = validate_behavior_aggregates()
    ctx = {
        "aggregate_validation_issues": aggregate_issues,
        "top_pandits": AdminIntelligenceService.get_top_performing_pandits(limit=10),
        "conversion": AdminIntelligenceService.get_booking_conversion_stats(),
        "trending_poojas": AdminIntelligenceService.get_trending_poojas(limit=10),
        "user_engagement": AdminIntelligenceService.get_user_engagement_metrics(),
        "platform_growth": AdminIntelligenceService.get_platform_growth_metrics(),
        "user_interest_distribution": AdminIntelligenceService.get_user_interest_distribution(limit_per_type=10),
        "pandit_engagement_trends": AdminIntelligenceService.get_pandit_engagement_trends(limit=20, days=30),
        "search_trend_intelligence": AdminIntelligenceService.get_search_trend_intelligence(limit=20, days=30),
        "user_engagement_trends": AdminIntelligenceService.get_user_engagement_trends(days=30),
        "content_popularity": AdminIntelligenceService.get_content_popularity_metrics(limit=20, days=30),
        "user_interest_insights": AdminIntelligenceService.get_user_interest_insights(limit_per_type=10),
        "feed_performance": AdminIntelligenceService.get_feed_performance_metrics(),
    }
    return render(request, "admin_intelligence/dashboard.html", ctx)


def _limit(request, default=10, max_val=50):
    return min(int(request.GET.get("limit", default)), max_val)


@staff_member_required
@require_GET
@cache_page(120)
def top_pandits(request):
    data = AdminIntelligenceService.get_top_performing_pandits(limit=_limit(request))
    return JsonResponse({"results": data})


@staff_member_required
@require_GET
@cache_page(120)
def conversion(request):
    data = AdminIntelligenceService.get_booking_conversion_stats()
    return JsonResponse(data)


@staff_member_required
@require_GET
@cache_page(120)
def trending_poojas(request):
    data = AdminIntelligenceService.get_trending_poojas(limit=_limit(request))
    return JsonResponse({"results": data})


@staff_member_required
@require_GET
@cache_page(120)
def user_engagement(request):
    data = AdminIntelligenceService.get_user_engagement_metrics()
    return JsonResponse(data)


@staff_member_required
@require_GET
@cache_page(120)
def platform_growth(request):
    data = AdminIntelligenceService.get_platform_growth_metrics()
    return JsonResponse(data)


@staff_member_required
@require_GET
@cache_page(120)
def pandit_engagement_trends(request):
    limit = min(int(request.GET.get("limit", 20)), 50)
    days = min(int(request.GET.get("days", 30)), 90)
    data = AdminIntelligenceService.get_pandit_engagement_trends(limit=limit, days=days)
    return JsonResponse({"results": data})


@staff_member_required
@require_GET
@cache_page(120)
def search_trends(request):
    limit = min(int(request.GET.get("limit", 20)), 50)
    days = min(int(request.GET.get("days", 30)), 90)
    data = AdminIntelligenceService.get_search_trend_intelligence(limit=limit, days=days)
    return JsonResponse({"results": data})


@staff_member_required
@require_GET
@cache_page(120)
def user_engagement_trends(request):
    days = min(int(request.GET.get("days", 30)), 90)
    data = AdminIntelligenceService.get_user_engagement_trends(days=days)
    return JsonResponse({"results": data})


@staff_member_required
@require_GET
@cache_page(120)
def content_popularity(request):
    limit = min(int(request.GET.get("limit", 20)), 50)
    days = min(int(request.GET.get("days", 30)), 90)
    data = AdminIntelligenceService.get_content_popularity_metrics(limit=limit, days=days)
    return JsonResponse({"results": data})


@staff_member_required
@require_GET
@cache_page(120)
def user_interest_insights(request):
    limit = min(int(request.GET.get("limit", 10)), 30)
    data = AdminIntelligenceService.get_user_interest_insights(limit_per_type=limit)
    return JsonResponse(data)


@staff_member_required
@require_GET
@cache_page(120)
def feed_performance(request):
    data = AdminIntelligenceService.get_feed_performance_metrics()
    return JsonResponse(data)
