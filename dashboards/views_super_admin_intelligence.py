"""
Super Admin Intelligence Dashboard — platform UI (not Django Admin).
Uses AdminIntelligenceService; read-only. Staff-only.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from admin_intelligence.services import AdminIntelligenceService
from behavior_engine.data_validation import validate_behavior_aggregates


@staff_member_required
def intelligence_dashboard(request):
    """Renders the Intelligence Dashboard inside the platform UI (base.html)."""
    aggregate_issues = validate_behavior_aggregates()
    context = {
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
    return render(
        request,
        "module5_dashboards/dashboard_intelligence.html",
        context,
    )
