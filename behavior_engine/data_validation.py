"""
Behavioral aggregate data validation.

Run before dashboards load or as a health check to detect missing or stale aggregates.
DO NOT query UserBehaviorEvent / UserContentInteraction here; only validate aggregate tables.
"""
from django.utils import timezone
from datetime import timedelta

from .models import (
    PanditEngagementDaily,
    SearchTrendDaily,
    UserEngagementDaily,
    ContentInteractionDaily,
)

STALE_DAYS_THRESHOLD = 2


def validate_behavior_aggregates():
    """
    Check aggregate tables for obvious anomalies (e.g. empty when expected, stale data).
    Returns list of issue strings; empty list means no issues detected.
    """
    issues = []
    today = timezone.now().date()
    stale_cutoff = today - timedelta(days=STALE_DAYS_THRESHOLD)

    if PanditEngagementDaily.objects.count() == 0:
        issues.append("Pandit engagement aggregates missing (no rows)")
    else:
        latest = PanditEngagementDaily.objects.order_by("-date").first()
        if latest and latest.date < stale_cutoff:
            issues.append(
                "Pandit engagement aggregates appear stale (latest older than 2 days)"
            )

    if SearchTrendDaily.objects.count() == 0:
        issues.append("Search trend aggregates missing (no rows)")
    else:
        latest = SearchTrendDaily.objects.order_by("-date").first()
        if latest and latest.date < stale_cutoff:
            issues.append(
                "Search trend aggregates appear stale (latest older than 2 days)"
            )

    if UserEngagementDaily.objects.count() == 0:
        issues.append("User engagement aggregates missing (no rows)")
    else:
        latest = UserEngagementDaily.objects.order_by("-date").first()
        if latest and latest.date < stale_cutoff:
            issues.append(
                "User engagement aggregates appear stale (latest older than 2 days)"
            )

    if ContentInteractionDaily.objects.count() == 0:
        issues.append("Content interaction aggregates missing (no rows)")
    else:
        latest = ContentInteractionDaily.objects.order_by("-date").first()
        if latest and latest.date < stale_cutoff:
            issues.append(
                "Content interaction aggregates appear stale (latest older than 2 days)"
            )

    return issues
