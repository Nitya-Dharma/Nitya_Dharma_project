"""
User Interest Scoring Engine. Converts behavior events into structured interest scores.
Reads from behavior tables only; writes to UserInterestSignal. Used by batch jobs.
Weights: profile_view +1, search_click +2, content_click +3, long_dwell +2, booking_intent +5,
review_expand +2, save +5, share +6; scroll_depth > 70% → +1.
Interest signals remain long-term; raw events may be archived after 90 days.
"""
import logging
from django.db.models import F
from django.utils import timezone
from datetime import timedelta

from behavior_engine.models import (
    UserBehaviorEvent,
    UserContentInteraction,
    UserInterestSignal,
    InterestScoringCheckpoint,
    InterestDecayCheckpoint,
    EVENT_PANDIT_PROFILE_VIEW,
    EVENT_SEARCH_RESULT_CLICK,
    EVENT_BOOKING_INTENT_SENT,
    EVENT_REVIEW_VIEW,
)

logger = logging.getLogger(__name__)

# Scoring weights (additive)
WEIGHT_PROFILE_VIEW = 1
WEIGHT_SEARCH_CLICK = 2
WEIGHT_CONTENT_CLICK = 3
WEIGHT_LONG_DWELL = 2   # dwell_time_ms > 15000
WEIGHT_BOOKING_INTENT = 5
WEIGHT_REVIEW_EXPAND = 2
WEIGHT_SAVE = 5
WEIGHT_SHARE = 6
WEIGHT_SCROLL_DEPTH = 1  # scroll_depth > 70
DWELL_THRESHOLD_MS = 15000
SCROLL_THRESHOLD_PCT = 70
DECAY_FACTOR_PER_WEEK = 0.95


def _normalize_value(val, max_len=100):
    if val is None:
        return ""
    s = str(val).strip()[:max_len]
    return s or "unknown"


class UserInterestScoringService:
    """
    Converts behavior events into UserInterestSignal scores.
    Call from batch jobs only; does not run in request cycle.
    """

    @staticmethod
    def update_interest_score(user, interest_type, interest_value, delta):
        """Add delta to existing score (or set to delta if new). User must be authenticated."""
        if not user or not getattr(user, "is_authenticated", True) or not user.is_authenticated:
            return
        if not interest_type or interest_value is None:
            return
        try:
            it = _normalize_value(interest_type, 50)
            iv = _normalize_value(interest_value, 100)
            if not it or not iv:
                return
            obj = UserInterestSignal.objects.filter(
                user=user, interest_type=it, interest_value=iv
            ).first()
            if obj:
                UserInterestSignal.objects.filter(pk=obj.pk).update(
                    score=F("score") + float(delta)
                )
            else:
                UserInterestSignal.objects.create(
                    user=user, interest_type=it, interest_value=iv, score=float(delta)
                )
        except Exception as e:
            logger.debug("update_interest_score failed: %s", e, exc_info=False)

    @staticmethod
    def _get_pandit_interest_context(profile_id):
        """Resolve pandit profile to pooja categories and cities for interest signals."""
        try:
            from profiles.models import PanditProfile
            profile = PanditProfile.objects.filter(id=profile_id).select_related().prefetch_related(
                "poojas_performed__pooja_category", "cities_served"
            ).first()
            if not profile:
                return None
            pooja_categories = set()
            for pooja in profile.poojas_performed.all():
                if pooja.pooja_category_id and pooja.pooja_category:
                    pooja_categories.add(_normalize_value(pooja.pooja_category.name))
                elif pooja.name:
                    pooja_categories.add(_normalize_value(pooja.name))
            cities = [_normalize_value(c.name) for c in profile.cities_served.all()[:10] if c.name]
            return {
                "pandit_id": profile_id,
                "pooja_categories": list(pooja_categories),
                "cities": cities,
            }
        except Exception as e:
            logger.debug("_get_pandit_interest_context failed: %s", e, exc_info=False)
            return None

    @staticmethod
    def process_behavior_event(event):
        """
        Process one UserBehaviorEvent and update UserInterestSignal.
        event: UserBehaviorEvent instance (with user, event_type, object_type, object_id).
        """
        if not event.user_id:
            return
        user = event.user
        delta = 0
        if event.event_type == EVENT_PANDIT_PROFILE_VIEW:
            delta = WEIGHT_PROFILE_VIEW
        elif event.event_type == EVENT_SEARCH_RESULT_CLICK:
            delta = WEIGHT_SEARCH_CLICK
        elif event.event_type == EVENT_BOOKING_INTENT_SENT:
            delta = WEIGHT_BOOKING_INTENT
        elif event.event_type == EVENT_REVIEW_VIEW:
            delta = WEIGHT_REVIEW_EXPAND
        else:
            return
        if delta <= 0:
            return
        if event.object_type == "pandit_profile" and event.object_id is not None:
            ctx = UserInterestScoringService._get_pandit_interest_context(event.object_id)
            if ctx:
                UserInterestScoringService.update_interest_score(
                    user, "pandit", str(ctx["pandit_id"]), delta
                )
                for cat in ctx.get("pooja_categories") or []:
                    UserInterestScoringService.update_interest_score(
                        user, "pooja_category", cat, delta
                    )
                for city in ctx.get("cities") or []:
                    UserInterestScoringService.update_interest_score(user, "city", city, delta)
            else:
                UserInterestScoringService.update_interest_score(
                    user, "pandit", str(event.object_id), delta
                )

    @staticmethod
    def process_content_interaction(interaction):
        """
        Process one UserContentInteraction and update UserInterestSignal.
        Applies content_click, dwell bonus, scroll bonus, save, share, expand_reviews.
        """
        if not interaction.user_id:
            return
        user = interaction.user
        delta = 0
        it = (interaction.interaction_type or "").lower()
        if it == "click":
            delta = WEIGHT_CONTENT_CLICK
        elif it == "view":
            delta = WEIGHT_PROFILE_VIEW
        elif it == "save":
            delta = WEIGHT_SAVE
        elif it == "share":
            delta = WEIGHT_SHARE
        elif it == "expand_reviews":
            delta = WEIGHT_REVIEW_EXPAND
        elif it == "impression":
            pass
        if (interaction.dwell_time_ms or 0) > DWELL_THRESHOLD_MS:
            delta += WEIGHT_LONG_DWELL
        if (interaction.scroll_depth or 0) > SCROLL_THRESHOLD_PCT:
            delta += WEIGHT_SCROLL_DEPTH
        if delta <= 0 and it not in ("click", "view", "save", "share", "expand_reviews"):
            return
        if interaction.content_type == "pandit_profile" and interaction.content_id is not None:
            ctx = UserInterestScoringService._get_pandit_interest_context(interaction.content_id)
            if ctx:
                UserInterestScoringService.update_interest_score(
                    user, "pandit", str(ctx["pandit_id"]), delta
                )
                for cat in ctx.get("pooja_categories") or []:
                    UserInterestScoringService.update_interest_score(
                        user, "pooja_category", cat, delta
                    )
                for city in ctx.get("cities") or []:
                    UserInterestScoringService.update_interest_score(user, "city", city, delta)
            else:
                UserInterestScoringService.update_interest_score(
                    user, "pandit", str(interaction.content_id), delta
                )

    @staticmethod
    def recalculate_user_interest(user, apply_decay=True):
        """
        Apply weekly decay to all interest signals for a user (score *= 0.95).
        Optionally call after processing new events to keep signals fresh.
        For global weekly decay use apply_weekly_decay() instead.
        """
        if not user or not getattr(user, "is_authenticated", True) or not user.is_authenticated:
            return
        try:
            if apply_decay:
                UserInterestSignal.objects.filter(user=user).update(
                    score=F("score") * DECAY_FACTOR_PER_WEEK
                )
        except Exception as e:
            logger.debug("recalculate_user_interest decay failed: %s", e, exc_info=False)


def apply_weekly_decay():
    """
    Apply score *= 0.95 to all UserInterestSignal rows at most once per 7 days.
    Uses InterestDecayCheckpoint; skips if last decay was less than 7 days ago.
    """
    try:
        checkpoint, _ = InterestDecayCheckpoint.objects.get_or_create(
            job_name="interest_decay",
            defaults={"last_decay_at": None},
        )
        now = timezone.now()
        if checkpoint.last_decay_at:
            days_since_decay = (now - checkpoint.last_decay_at).days
            if days_since_decay < 7:
                return
        UserInterestSignal.objects.update(score=F("score") * DECAY_FACTOR_PER_WEEK)
        checkpoint.last_decay_at = now
        checkpoint.save(update_fields=["last_decay_at", "updated_at"])
    except Exception as e:
        logger.debug("apply_weekly_decay failed: %s", e, exc_info=False)


def update_user_interest_scores(since_days=7, batch_size=500, apply_decay=False):
    """
    Batch job: fetch only new behavior events since last_processed_at, compute interest signals.
    Uses InterestScoringCheckpoint to avoid duplicate scoring. Run during midnight batch (e.g. 02:30).
    apply_decay: if True, run apply_weekly_decay() once (decay runs at most once per 7 days).
    """
    checkpoint, _ = InterestScoringCheckpoint.objects.get_or_create(
        job_name="user_interest_scoring",
        defaults={"last_processed_at": None},
    )
    start_time = checkpoint.last_processed_at
    if start_time is None:
        start_time = timezone.now() - timedelta(days=since_days)
    processed_users = set()

    # Process only new UserBehaviorEvent (created_at > start_time)
    events = (
        UserBehaviorEvent.objects.filter(
            created_at__gt=start_time, user_id__isnull=False
        )
        .select_related("user")
        .order_by("created_at")[: batch_size * 2]
    )
    for event in events:
        UserInterestScoringService.process_behavior_event(event)
        if event.user_id:
            processed_users.add(event.user_id)

    # Process only new UserContentInteraction (created_at > start_time)
    interactions = (
        UserContentInteraction.objects.filter(
            created_at__gt=start_time, user_id__isnull=False
        )
        .select_related("user")
        .order_by("created_at")[: batch_size * 2]
    )
    for interaction in interactions:
        UserInterestScoringService.process_content_interaction(interaction)
        if interaction.user_id:
            processed_users.add(interaction.user_id)

    checkpoint.last_processed_at = timezone.now()
    checkpoint.save(update_fields=["last_processed_at", "updated_at"])

    if apply_decay:
        apply_weekly_decay()
    return len(processed_users)
