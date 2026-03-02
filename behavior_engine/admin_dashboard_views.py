"""
Super Admin Analytics Dashboard — reads from behavior_event_log only.
No modification to raw events. Super Admin only; aggregation queries.
Extends with Behavior Intelligence (Newsfeed Engine Insights) section.
"""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from .models import BehaviorEvent
from .aggregation import get_behavior_intelligence_context, get_share_analytics


@login_required
def super_admin_analytics_dashboard(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    last_7_days = timezone.now() - timedelta(days=7)

    total_events = BehaviorEvent.objects.count()

    events_last_7_days = BehaviorEvent.objects.filter(
        created_at__gte=last_7_days
    ).count()

    top_event_types = (
        BehaviorEvent.objects
        .values("event_type")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    top_entities = (
        BehaviorEvent.objects
        .exclude(entity_type__isnull=True)
        .exclude(entity_type="")
        .values("entity_type", "entity_id")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    behavior_intelligence = get_behavior_intelligence_context()

    # Referral tier analytics (read-only from referrals app)
    try:
        from referrals.analytics import get_referral_tier_analytics
        referral_tier_analytics = get_referral_tier_analytics()
    except Exception:
        referral_tier_analytics = None

    # Share analytics (share_click events)
    share_analytics = get_share_analytics()

    context = {
        "dashboard_has_data": True,
        "total_events": total_events,
        "events_last_7_days": events_last_7_days,
        "top_event_types": top_event_types,
        "top_entities": top_entities,
        "behavior_intelligence": behavior_intelligence,
        "referral_tier_analytics": referral_tier_analytics,
        "share_analytics": share_analytics,
    }

    return render(
        request,
        "superadmin/analytics_dashboard.html",
        context,
    )
