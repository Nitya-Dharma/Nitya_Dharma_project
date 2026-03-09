"""
Phase 13: Admin analytics URL routes. All endpoints require Admin or Super Admin.
"""
from django.urls import path
from . import views

app_name = "analytics_dashboard"

urlpatterns = [
    path("trending-searches/", views.trending_searches_view, name="trending_searches"),
    path("top-clicked-pandits/", views.top_clicked_pandits_view, name="top_clicked_pandits"),
    path("top-reviewed-pandits/", views.top_reviewed_pandits_view, name="top_reviewed_pandits"),
    path("city-activity/", views.city_activity_view, name="city_activity"),
    path("booking-stats/", views.booking_stats_view, name="booking_stats"),
    path("user-engagement/", views.user_engagement_view, name="user_engagement"),
]
