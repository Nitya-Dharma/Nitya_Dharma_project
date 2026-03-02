"""
Behavior Intelligence — read-only KPI aggregation from behavior_event_log.
No writes to raw events. No search/trust/governance/recommendation coupling.
Used only by Super Admin Analytics Dashboard.
"""

from datetime import timedelta
from django.db.models import Count
from django.utils import timezone

from .models import BehaviorEvent


def _range_days(days):
    return timezone.now() - timedelta(days=days)


def get_engagement_metrics():
    """User Engagement Metrics — from behavior_event_log only."""
    qs = BehaviorEvent.objects.all()
    since_1d = _range_days(1)
    since_7d = _range_days(7)
    since_30d = _range_days(30)

    def distinct_count(field, since):
        return qs.filter(created_at__gte=since).values(field).distinct().count()

    dau_users = distinct_count("user_id", since_1d)
    wau_users = distinct_count("user_id", since_7d)
    mau_users = distinct_count("user_id", since_30d)
    dau_sessions = distinct_count("session_id", since_1d)
    wau_sessions = distinct_count("session_id", since_7d)
    mau_sessions = distinct_count("session_id", since_30d)

    scroll_25 = qs.filter(event_type="scroll_depth", metadata__percent=25).count()
    scroll_50 = qs.filter(event_type="scroll_depth", metadata__percent=50).count()
    scroll_75 = qs.filter(event_type="scroll_depth", metadata__percent=75).count()
    scroll_100 = qs.filter(event_type="scroll_depth", metadata__percent=100).count()

    total_sessions_7d = wau_sessions or 1
    total_events_7d = qs.filter(created_at__gte=since_7d).count()
    sessions_per_user = round(total_events_7d / total_sessions_7d, 1) if total_sessions_7d else "—"

    return {
        "dau": dau_users,
        "wau": wau_users,
        "mau": mau_users,
        "dau_sessions": dau_sessions,
        "wau_sessions": wau_sessions,
        "mau_sessions": mau_sessions,
        "avg_session_duration": "—",
        "sessions_per_user": sessions_per_user,
        "bounce_rate": "—",
        "scroll_depth_25": scroll_25,
        "scroll_depth_50": scroll_50,
        "scroll_depth_75": scroll_75,
        "scroll_depth_100": scroll_100,
        "retention_d1": "—",
        "retention_d7": "—",
        "retention_d30": "—",
        "repeat_visit_rate": "—",
        "dwell_time_avg": "—",
    }


def get_content_interaction_metrics():
    """Content Interaction Metrics — from behavior_event_log only."""
    qs = BehaviorEvent.objects.filter(created_at__gte=_range_days(30))
    pandit_views = qs.filter(entity_type="pandit").count()
    temple_views = qs.filter(entity_type="temple").count()
    pooja_views = qs.filter(entity_type="pooja").count()
    card_clicks = qs.filter(event_type="pandit_card_click").count() + qs.filter(event_type="temple_view").count()
    follow_clicks = qs.filter(event_type="follow_click").count()
    page_views = qs.filter(event_type="page_view").count()
    card_click_rate = round(100 * card_clicks / page_views, 1) if page_views else "—"
    follow_rate = round(100 * follow_clicks / (pandit_views or 1), 1) if pandit_views else "—"
    top_entities = (
        qs.exclude(entity_type__isnull=True)
        .exclude(entity_type="")
        .values("entity_type", "entity_id")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )
    return {
        "pandit_profile_views": pandit_views,
        "temple_views": temple_views,
        "pooja_views": pooja_views,
        "card_click_rate": card_click_rate,
        "follow_rate": follow_rate,
        "save_rate": "—",
        "share_rate": "—",
        "top_viewed_entities": list(top_entities),
        "engagement_score_per_entity": "—",
    }


def get_behavioral_intent_metrics():
    """Behavioral Intent Metrics — from behavior_event_log only."""
    qs = BehaviorEvent.objects.filter(created_at__gte=_range_days(30))
    booking_intent = qs.filter(event_type="booking_intent_click").count()
    profile_visits = qs.exclude(entity_type__isnull=True).exclude(entity_type="").count()
    return {
        "booking_intent_clicks": booking_intent,
        "booking_submission_rate": "—",
        "high_intent_users_pct": "—",
        "repeat_profile_visits": "—",
        "scroll_75_click_correlation": "—",
        "intent_depth_index": "—",
    }


def get_newsfeed_intelligence_metrics():
    """Newsfeed Intelligence Metrics — from behavior_event_log only."""
    qs = BehaviorEvent.objects.filter(created_at__gte=_range_days(7))
    top_entities = list(
        qs.exclude(entity_type__isnull=True)
        .exclude(entity_type="")
        .values("entity_type", "entity_id")
        .annotate(total=Count("id"))
        .order_by("-total")[:20]
    )
    popularity_score = sum(e["total"] for e in top_entities)
    return {
        "user_interest_score_agg": "—",
        "entity_popularity_score": popularity_score,
        "trending_score": "—",
        "recency_decay_index": "—",
        "geo_preference_distribution": "—",
        "category_affinity": "—",
        "feed_ctr": "—",
        "cold_start_users_pct": "—",
    }


def get_performance_event_health():
    """Performance & Event Health — from behavior_event_log only."""
    qs = BehaviorEvent.objects.all()
    last_hour = qs.filter(created_at__gte=_range_days(0) + timedelta(hours=23))
    events_last_hour = last_hour.count()
    events_per_minute = round(events_last_hour / 60.0, 1) if events_last_hour else 0
    return {
        "events_per_minute": events_per_minute,
        "failed_tracking_pct": "—",
        "invalid_payload_pct": "—",
        "duplicate_events_pct": "—",
        "tracking_opt_out_pct": "—",
        "avg_event_write_time": "—",
    }


def get_referral_impact_metrics():
    """Referral Impact — no referral data in behavior_engine."""
    return {
        "referred_users_engagement": "—",
        "referral_booking_conversion": "—",
        "trust_chain_depth_vs_activity": "—",
        "top_referrers_by_engagement": "—",
    }


def get_platform_decision_insights():
    """Platform Decision Insights — from behavior_event_log only."""
    qs = BehaviorEvent.objects.filter(created_at__gte=_range_days(30))
    exit_pages = list(
        qs.values("page_url").annotate(total=Count("id")).order_by("-total")[:5]
    )
    return {
        "high_exit_pages": exit_pages,
        "low_engagement_cities": "—",
        "underperforming_categories": "—",
        "high_view_low_booking_entities": "—",
        "feed_vs_search_usage_ratio": "—",
    }


def get_behavior_intelligence_context():
    """Returns full context dict for Behavior Intelligence section (read-only)."""
    return {
        "engagement": get_engagement_metrics(),
        "content_interaction": get_content_interaction_metrics(),
        "behavioral_intent": get_behavioral_intent_metrics(),
        "newsfeed_intelligence": get_newsfeed_intelligence_metrics(),
        "performance_health": get_performance_event_health(),
        "referral_impact": get_referral_impact_metrics(),
        "platform_insights": get_platform_decision_insights(),
    }


def get_share_analytics():
    """
    Share analytics from behavior_event_log (event_type=share_click).
    Read-only: total shares, by platform, top shared entities.
    """
    qs = BehaviorEvent.objects.filter(event_type="share_click")
    total_shares = qs.count()

    # By platform (metadata.platform)
    share_events = qs.values_list("metadata", flat=True)
    shares_by_platform = {}
    for m in share_events:
        p = (m or {}).get("platform") or "unknown"
        shares_by_platform[p] = shares_by_platform.get(p, 0) + 1
    shares_by_platform = [{"platform": k, "count": v} for k, v in sorted(shares_by_platform.items(), key=lambda x: -x[1])]

    # Top shared entities (entity_type + entity_id)
    top_shared_entities = list(
        qs.values("entity_type", "entity_id")
        .annotate(total=Count("id"))
        .order_by("-total")[:15]
    )

    # Top shared Pandits (entity_type=pandit)
    top_shared_pandits = list(
        qs.filter(entity_type="pandit")
        .values("entity_id")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    # Top shared Temples/Pages (entity_type=temple or page)
    top_shared_temples = list(
        qs.filter(entity_type__in=["temple", "page"])
        .values("entity_id")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    return {
        "total_shares": total_shares,
        "shares_by_platform": shares_by_platform,
        "top_shared_entities": top_shared_entities,
        "top_shared_pandits": top_shared_pandits,
        "top_shared_temples": top_shared_temples,
    }
