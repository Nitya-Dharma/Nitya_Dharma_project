"""
Behavior Engine — Raw event storage for future Newsfeed Intelligence.
All tables use prefix behavior_*. Isolated from existing analytics app.
Phase 14: UserBehaviorEvent for server-side behavior analytics (search, profile, booking, etc.).
"""

from django.db import models
from django.conf import settings


# Phase 14: Event type constants for UserBehaviorEvent (behavior analytics engine)
EVENT_SEARCH_QUERY = "search_query"
EVENT_SEARCH_RESULT_CLICK = "search_result_click"
EVENT_PANDIT_PROFILE_VIEW = "pandit_profile_view"
EVENT_BOOKING_INTENT_SENT = "booking_intent_sent"
EVENT_REVIEW_VIEW = "review_view"
EVENT_PAGE_VIEW = "page_view"


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


class UserBehaviorEvent(models.Model):
    """
    Phase 14: Generic behavior event for analytics (search, profile views, booking, reviews, page views).
    Passive recording only; never blocks requests. Events older than 90 days may be archived later.
    """
    event_type = models.CharField(max_length=50, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="behavior_analytics_events",
    )
    session_id = models.CharField(max_length=120, null=True, blank=True, db_index=True)
    object_type = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    object_id = models.IntegerField(null=True, blank=True, db_index=True)
    metadata = models.JSONField(null=True, blank=True, default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "behavior_user_behavior_event"
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["object_type", "object_id"]),
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


# --- Phase 14.x: Advanced behavior data for personalized newsfeed (additive only) ---
# Raw events older than 90 days may be archived later. Do not implement deletion yet.


class UserContentInteraction(models.Model):
    """
    Phase 14.x: Detailed interaction between users and content (pandits, poojas, search results).
    Append-only. Events older than 90 days may be archived later.
    Interaction types: view, click, impression, save, share, like, expand_reviews.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="behavior_content_interactions",
    )
    session_id = models.CharField(max_length=120, null=True, blank=True, db_index=True)
    content_type = models.CharField(max_length=50, db_index=True)
    content_id = models.IntegerField(db_index=True)
    interaction_type = models.CharField(max_length=50, db_index=True)
    dwell_time_ms = models.IntegerField(null=True, blank=True)
    scroll_depth = models.IntegerField(null=True, blank=True)
    position_in_list = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "behavior_user_content_interaction"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["content_type", "content_id"]),
            models.Index(fields=["interaction_type", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.interaction_type} {self.content_type}:{self.content_id} @ {self.created_at}"


class UserFeedImpression(models.Model):
    """
    Phase 14.x: What items were shown to users in a feed (for ranking training).
    Append-only. Events older than 90 days may be archived later.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="behavior_feed_impressions",
    )
    session_id = models.CharField(max_length=120, null=True, blank=True, db_index=True)
    content_type = models.CharField(max_length=50, db_index=True)
    content_id = models.IntegerField(db_index=True)
    feed_type = models.CharField(max_length=50, db_index=True)
    feed_position = models.IntegerField()
    was_clicked = models.BooleanField(default=False)
    was_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "behavior_user_feed_impression"
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["feed_type", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.feed_type} pos={self.feed_position} @ {self.created_at}"


class UserSessionAnalytics(models.Model):
    """
    Phase 14.x: High-level session analytics. Append-only.
    Events older than 90 days may be archived later.
    """
    session_id = models.CharField(max_length=120, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="behavior_session_analytics",
    )
    session_start = models.DateTimeField()
    session_end = models.DateTimeField()
    events_count = models.IntegerField(default=0)
    page_views = models.IntegerField(default=0)
    search_queries = models.IntegerField(default=0)
    total_dwell_time_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "behavior_user_session_analytics"
        indexes = [
            models.Index(fields=["session_id"]),
            models.Index(fields=["user", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"session {self.session_id} @ {self.created_at}"


class UserInterestSignal(models.Model):
    """
    Phase 14.x: Aggregated interest signals per user (for recommendation ranking).
    Example: interest_type=pooja_category, interest_value=ganesh_pooja; interest_type=city, interest_value=hyderabad.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="behavior_interest_signals",
    )
    interest_type = models.CharField(max_length=50, db_index=True)
    interest_value = models.CharField(max_length=100, db_index=True)
    score = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behavior_user_interest_signal"
        indexes = [
            models.Index(fields=["user", "interest_type"]),
        ]
        ordering = ["user", "interest_type"]
        unique_together = [["user", "interest_type", "interest_value"]]

    def __str__(self):
        return f"{self.user_id} {self.interest_type}={self.interest_value} ({self.score})"


class InterestScoringCheckpoint(models.Model):
    """
    Tracks last processed timestamp for interest scoring batch job.
    Prevents duplicate scoring of the same behavior events.
    """
    job_name = models.CharField(max_length=100, unique=True)
    last_processed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behavior_interest_scoring_checkpoint"

    def __str__(self):
        return f"{self.job_name} @ {self.last_processed_at}"


class InterestDecayCheckpoint(models.Model):
    """
    Tracks last run of weekly interest decay. Decay runs only once per 7+ days.
    """
    job_name = models.CharField(max_length=100, unique=True)
    last_decay_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behavior_interest_decay_checkpoint"

    def __str__(self):
        return f"{self.job_name} @ {self.last_decay_at}"


# --- Aggregated intelligence (derived from raw behavior). Raw events > 90 days may be archived; aggregates retained. ---


class PanditEngagementDaily(models.Model):
    """Daily aggregated engagement per pandit (PanditProfile.id). Derived from behavior events."""
    pandit_id = models.IntegerField(db_index=True)
    date = models.DateField(db_index=True)
    profile_views = models.IntegerField(default=0)
    search_clicks = models.IntegerField(default=0)
    booking_intents = models.IntegerField(default=0)
    review_views = models.IntegerField(default=0)
    avg_dwell_time_ms = models.IntegerField(default=0)
    engagement_score = models.FloatField(default=0)

    class Meta:
        db_table = "behavior_pandit_engagement_daily"
        indexes = [
            models.Index(fields=["pandit_id", "date"]),
            models.Index(fields=["date"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["pandit_id", "date"], name="uniq_pandit_engagement_day"),
        ]
        ordering = ["-date", "-engagement_score"]

    def __str__(self):
        return f"pandit={self.pandit_id} date={self.date} score={self.engagement_score}"


class SearchTrendDaily(models.Model):
    """Daily trending search queries. Derived from search + behavior."""
    query = models.CharField(max_length=200, db_index=True)
    date = models.DateField(db_index=True)
    search_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    conversion_count = models.IntegerField(default=0)

    class Meta:
        db_table = "behavior_search_trend_daily"
        indexes = [
            models.Index(fields=["query", "date"]),
            models.Index(fields=["date"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["query", "date"], name="uniq_searchtrend_query_day"),
        ]
        ordering = ["-date", "-search_count"]

    def __str__(self):
        return f"{self.query} @ {self.date}"


class UserEngagementDaily(models.Model):
    """Daily platform-wide engagement. One row per date."""
    date = models.DateField(db_index=True)
    active_users = models.IntegerField(default=0)
    total_sessions = models.IntegerField(default=0)
    total_page_views = models.IntegerField(default=0)
    total_searches = models.IntegerField(default=0)
    total_interactions = models.IntegerField(default=0)
    avg_session_duration_ms = models.IntegerField(default=0)

    class Meta:
        db_table = "behavior_user_engagement_daily"
        constraints = [
            models.UniqueConstraint(fields=["date"], name="uniq_user_engagement_day"),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"engagement @ {self.date}"


class ContentInteractionDaily(models.Model):
    """Daily aggregated interactions per content (e.g. pandit_profile, content_id)."""
    content_type = models.CharField(max_length=50, db_index=True)
    content_id = models.IntegerField(db_index=True)
    date = models.DateField(db_index=True)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    saves = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    avg_dwell_time_ms = models.IntegerField(default=0)

    class Meta:
        db_table = "behavior_content_interaction_daily"
        indexes = [
            models.Index(fields=["content_type", "content_id"]),
            models.Index(fields=["date"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["content_type", "content_id", "date"], name="uniq_content_interaction_day"),
        ]
        ordering = ["-date", "-clicks"]

    def __str__(self):
        return f"{self.content_type}:{self.content_id} @ {self.date}"


class UserInterestAggregate(models.Model):
    """Aggregated interest signals per user (snapshot from UserInterestSignal for fast dashboard queries)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="behavior_interest_aggregates",
    )
    interest_type = models.CharField(max_length=50, db_index=True)
    interest_value = models.CharField(max_length=100, db_index=True)
    interaction_count = models.IntegerField(default=0)
    score = models.FloatField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behavior_user_interest_aggregate"
        indexes = [
            models.Index(fields=["user_id", "interest_type"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "interest_type", "interest_value"], name="uniq_user_interest_value"),
        ]
        ordering = ["user", "interest_type"]

    def __str__(self):
        return f"user={self.user_id} {self.interest_type}={self.interest_value} ({self.score})"
