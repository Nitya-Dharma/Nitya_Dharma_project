"""
Behavior Engine — Raw event storage for future Newsfeed Intelligence.
All tables use prefix behavior_*. Isolated from existing analytics app.
"""

from django.db import models
from django.conf import settings


class BehaviorEvent(models.Model):
    """
    Raw behavior event storage. Used for engagement scoring and newsfeed ranking.
    No raw IP storage. Fails silently; does not block page rendering.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    session_id = models.CharField(max_length=120, db_index=True)

    event_type = models.CharField(max_length=80, db_index=True)

    entity_type = models.CharField(max_length=80, null=True, blank=True)
    entity_id = models.CharField(max_length=120, null=True, blank=True)

    page_url = models.TextField()
    page_title = models.TextField()

    referrer = models.TextField(null=True, blank=True)

    device_type = models.CharField(max_length=20, null=True, blank=True)
    browser = models.TextField(null=True, blank=True)
    os = models.CharField(max_length=50, null=True, blank=True)
    screen_resolution = models.CharField(max_length=30, null=True, blank=True)

    metadata = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "behavior_event_log"
        indexes = [
            models.Index(fields=["user", "event_type"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} @ {self.created_at}"


# --- Aggregation / snapshot models (read-only from dashboard; populated by jobs) ---
# Raw behavior_event_log remains append-only. These tables store derived aggregates only.


class UserInterestProfile(models.Model):
    """Aggregated interest profile per user (from behavior_event_log)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="behavior_interest_profiles",
    )
    date = models.DateField(db_index=True)
    interest_score = models.FloatField(default=0.0)
    category_affinity = models.JSONField(default=dict)
    geo_preference = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behavior_user_interest_profile"
        unique_together = [["user", "date"]]
        ordering = ["-date"]


class EntityPopularitySnapshot(models.Model):
    """Daily popularity snapshot per entity (from behavior_event_log)."""
    date = models.DateField(db_index=True)
    entity_type = models.CharField(max_length=80, db_index=True)
    entity_id = models.CharField(max_length=120, db_index=True)
    view_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    engagement_score = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behavior_entity_popularity_snapshot"
        unique_together = [["date", "entity_type", "entity_id"]]
        ordering = ["-date", "-engagement_score"]


class UserSessionMetrics(models.Model):
    """Session-level metrics derived from behavior_event_log."""
    session_id = models.CharField(max_length=120, db_index=True)
    date = models.DateField(db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    event_count = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    scroll_depth_max = models.PositiveSmallIntegerField(null=True, blank=True)
    page_views = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behavior_user_session_metrics"
        ordering = ["-date", "-updated_at"]


class TrendingSnapshotDaily(models.Model):
    """Daily trending score per entity (from behavior_event_log)."""
    date = models.DateField(db_index=True)
    entity_type = models.CharField(max_length=80, db_index=True)
    entity_id = models.CharField(max_length=120, db_index=True)
    trending_score = models.FloatField(default=0.0)
    recency_decay_index = models.FloatField(default=1.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behavior_trending_snapshot_daily"
        unique_together = [["date", "entity_type", "entity_id"]]
        ordering = ["-date", "-trending_score"]


class FeedImpressionLog(models.Model):
    """Log of feed impressions (populated when feed_impression events exist)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    session_id = models.CharField(max_length=120, db_index=True)
    entity_type = models.CharField(max_length=80, null=True, blank=True)
    entity_id = models.CharField(max_length=120, null=True, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    clicked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "behavior_feed_impression_log"
        ordering = ["-created_at"]
