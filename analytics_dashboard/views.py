"""
Phase 13: Admin analytics API views. Read-only; restricted to Admin Pandit and Super Admin.
"""
from django.http import JsonResponse

from accounts.utils import is_admin
from .services import AdminAnalyticsService
from . import serializers as s


def _admin_required(view_func):
    """Require authenticated user with role=admin or is_superuser. Return 403 otherwise."""
    def wrapped(request):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Authentication required", "message": "Admin or Super Admin access required"},
                status=403,
            )
        if not (is_admin(request.user) or request.user.is_superuser):
            return JsonResponse(
                {"error": "Forbidden", "message": "Admin or Super Admin access required"},
                status=403,
            )
        return view_func(request)
    return wrapped


def _json_response(payload):
    return JsonResponse(payload)


@_admin_required
def trending_searches_view(request):
    """GET /admin-analytics/trending-searches/"""
    data = AdminAnalyticsService.get_trending_searches(limit=10)
    if data is None:
        data = []
    return _json_response(s.format_trending_searches(data))


@_admin_required
def top_clicked_pandits_view(request):
    """GET /admin-analytics/top-clicked-pandits/"""
    data = AdminAnalyticsService.get_top_clicked_pandits(limit=10)
    if data is None:
        data = []
    return _json_response(s.format_top_clicked_pandits(data))


@_admin_required
def top_reviewed_pandits_view(request):
    """GET /admin-analytics/top-reviewed-pandits/"""
    data = AdminAnalyticsService.get_top_reviewed_pandits(limit=10)
    if data is None:
        data = []
    return _json_response(s.format_top_reviewed_pandits(data))


@_admin_required
def city_activity_view(request):
    """GET /admin-analytics/city-activity/"""
    data = AdminAnalyticsService.get_city_activity(limit=10)
    if data is None:
        data = []
    return _json_response(s.format_city_activity(data))


@_admin_required
def booking_stats_view(request):
    """GET /admin-analytics/booking-stats/"""
    data = AdminAnalyticsService.get_booking_stats()
    return _json_response(s.format_booking_stats(data))


@_admin_required
def user_engagement_view(request):
    """GET /admin-analytics/user-engagement/"""
    data = AdminAnalyticsService.get_user_engagement()
    if data is None:
        data = {}
    return _json_response(s.format_user_engagement(data))
