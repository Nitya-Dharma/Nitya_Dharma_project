"""
Phase 15: Recommendation algorithms. Read-only via BehaviorIntelligenceService (aggregated tables).
DO NOT query UserBehaviorEvent here; use behavior_engine.intelligence_service.
"""
from behavior_engine.intelligence_service import BehaviorIntelligenceService


def compute_trending_pandits(limit=10, days=7):
    """
    Score pandits from aggregated PanditEngagementDaily (last N days).
    score = profile_views*1 + search_clicks*2 + booking_intents*3.
    Returns list of (pandit_profile_id, score) ordered by score desc.
    """
    rows = BehaviorIntelligenceService.get_pandit_engagement_scores(days=days)
    scores = {}
    for r in rows:
        pid = r["pandit_id"]
        scores[pid] = (
            (r["profile_views"] or 0) * 1
            + (r["search_clicks"] or 0) * 2
            + (r["booking_intents"] or 0) * 3
        )
    sorted_ids = sorted(scores.keys(), key=lambda x: -scores[x])[:limit]
    return [(pid, scores[pid]) for pid in sorted_ids]
