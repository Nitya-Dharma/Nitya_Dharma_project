"""
Phase 16: Admin intelligence API routes. All require staff.
"""
from django.urls import path
from admin_intelligence import views

app_name = "admin_intelligence"

urlpatterns = [
    path("", views.dashboard_page),
    path("top-pandits/", views.top_pandits),
    path("conversion/", views.conversion),
    path("trending-poojas/", views.trending_poojas),
    path("user-engagement/", views.user_engagement),
    path("platform-growth/", views.platform_growth),
    path("pandit-engagement-trends/", views.pandit_engagement_trends),
    path("search-trends/", views.search_trends),
    path("user-engagement-trends/", views.user_engagement_trends),
    path("content-popularity/", views.content_popularity),
    path("user-interest-insights/", views.user_interest_insights),
    path("feed-performance/", views.feed_performance),
]
