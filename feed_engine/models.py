"""
Phase 17A: Feed ranking engine. Candidate items for personalized feeds.
Populated by precompute_feed_candidates(); ranked at request time.
"""
from django.db import models


class FeedItemCandidate(models.Model):
    """
    Candidate item that may appear in a user's feed.
    Scores are updated by nightly precompute; interest score applied at request time.
    """
    content_type = models.CharField(max_length=50, db_index=True)  # e.g. 'pandit', 'pooja'
    content_id = models.IntegerField(db_index=True)
    base_score = models.FloatField(default=0)
    popularity_score = models.FloatField(default=0)
    engagement_score = models.FloatField(default=0)
    freshness_score = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)  # for freshness / re-precompute
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feed_feeditemcandidate"
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "content_id"],
                name="uniq_feed_candidate",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "content_id"]),
            models.Index(fields=["content_type"]),
            models.Index(fields=["updated_at"]),
        ]
        ordering = ["-engagement_score", "-popularity_score"]

    def __str__(self):
        return f"{self.content_type}:{self.content_id}"
