"""
Behavior engine batch tasks. Run via admin scheduler (e.g. 02:30 AM).
Interest signals remain long-term; raw events may be archived after 90 days.
"""
import logging
from datetime import timedelta
from django.utils import timezone

from .interest_scoring import update_user_interest_scores
from .aggregation_services import run_daily_behavior_aggregation

logger = logging.getLogger(__name__)


def run_daily_behavior_aggregation_task(target_date=None, target_dates=None):
    """
    Run daily aggregation in a single transaction (idempotent).

    Default: aggregate yesterday only.
    For late-event handling, pass target_dates=[yesterday, day_before] to re-aggregate last 2 days.
    Example: run_daily_behavior_aggregation_task(target_dates=[yesterday, yesterday - timedelta(days=1)])
    """
    try:
        result = run_daily_behavior_aggregation(target_date=target_date, target_dates=target_dates)
        logger.info("run_daily_behavior_aggregation completed: %s", result)
        return result
    except Exception as e:
        logger.exception("run_daily_behavior_aggregation_task failed: %s", e)
        return {}


def update_user_interest_scores_task(since_days=7, batch_size=500, apply_decay=False):
    """
    Fetch recent behavior events and content interactions, compute interest signals,
    and optionally apply weekly decay. Intended to run at 02:30 AM.
    """
    try:
        count = update_user_interest_scores(
            since_days=since_days, batch_size=batch_size, apply_decay=apply_decay
        )
        logger.info("update_user_interest_scores processed %s users", count)
        return count
    except Exception as e:
        logger.exception("update_user_interest_scores_task failed: %s", e)
        return 0
