"""
Phase 17A: Feed engine batch tasks. Precompute candidates nightly.
Uses BehaviorIntelligenceService for engagement/popularity (aggregated tables).
"""
import logging
from django.utils import timezone
from datetime import timedelta

from feed_engine.models import FeedItemCandidate
from behavior_engine.intelligence_service import BehaviorIntelligenceService
from profiles.models import PanditProfile

logger = logging.getLogger(__name__)

CANDIDATE_POOL_SIZE = 200
DAYS_AGGREGATE = 7


def _normalize(value, min_val=0, max_val=1):
    """Safe normalization to [0, 1]; avoids division-by-zero when max_val is zero or None."""
    if max_val is None or max_val <= min_val:
        return 0.0
    try:
        normalized = (float(value) - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, normalized))
    except (ZeroDivisionError, TypeError, ValueError):
        return 0.0


def precompute_feed_candidates():
    """
    Nightly job: refresh FeedItemCandidate from approved pandits and aggregation tables.
    Limits pool to CANDIDATE_POOL_SIZE. Idempotent (update_or_create).
    """
    since = timezone.now().date() - timedelta(days=DAYS_AGGREGATE)
    # Approved pandit profile ids (limit 200)
    pandit_ids = list(
        PanditProfile.objects.filter(is_profile_approved=True)
        .values_list("id", flat=True)[:CANDIDATE_POOL_SIZE]
    )
    if not pandit_ids:
        logger.warning("precompute_feed_candidates: no approved pandits")
        return 0

    # Engagement and popularity from intelligence service (aggregated tables)
    engagement_by_id, popularity_by_id = BehaviorIntelligenceService.get_engagement_and_popularity_for_feed(
        days=DAYS_AGGREGATE, pandit_ids=pandit_ids
    )

    # Compute max values once for normalization
    eng_values = list(engagement_by_id.values()) or [0]
    pop_values = list(popularity_by_id.values()) or [0]
    max_engagement = max(eng_values) or 1
    max_popularity = max(pop_values) or 1

    count = 0
    for pid in pandit_ids:
        eng = engagement_by_id.get(pid, 0)
        pop = popularity_by_id.get(pid, 0)
        engagement_n = _normalize(eng, 0, max_engagement)
        popularity_n = _normalize(pop, 0, max_popularity)
        # Freshness: 1.0 for all when precomputed daily; or use 0.9 as default
        freshness_n = 0.9
        FeedItemCandidate.objects.update_or_create(
            content_type="pandit",
            content_id=pid,
            defaults={
                "base_score": 0,
                "popularity_score": popularity_n,
                "engagement_score": engagement_n,
                "freshness_score": freshness_n,
            },
        )
        count += 1
    logger.info("precompute_feed_candidates: updated %s candidates", count)
    return count
