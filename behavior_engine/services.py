"""
Phase 14: Behavior event tracking service. Passive recording; never raises.
Phase 14.x: Extended tracking for content interaction, feed impressions, session analytics, interest signals.
"""
import logging
from django.utils import timezone
from .models import (
    UserBehaviorEvent,
    UserContentInteraction,
    UserFeedImpression,
    UserSessionAnalytics,
    UserInterestSignal,
)

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_user_agent(request):
    if not request:
        return None
    return request.META.get("HTTP_USER_AGENT", "")[:500] or None


def _get_session_id(request):
    if not request or not getattr(request, "session", None):
        return None
    key = getattr(request.session, "session_key", None)
    if not key and hasattr(request.session, "save"):
        try:
            request.session.save()
            key = request.session.session_key
        except Exception:
            pass
    return key or None


def track_event(
    event_type,
    request=None,
    user=None,
    object_type=None,
    object_id=None,
    metadata=None,
):
    """
    Record a behavior event. Never raises; failures are logged and ignored.
    """
    try:
        uid = None
        session_id = None
        ip_address = None
        user_agent = None
        if request:
            uid = getattr(request, "user", None)
            if uid and not uid.is_authenticated:
                uid = None
            session_id = _get_session_id(request)
            ip_address = _get_client_ip(request)
            user_agent = _get_user_agent(request)
        if user is not None:
            uid = user
        meta = metadata if metadata is not None else {}
        data = {
            "event_type": event_type,
            "user_id": uid.pk if uid else None,
            "session_id": session_id,
            "object_type": object_type,
            "object_id": object_id,
            "metadata": meta,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
        try:
            # NOTE:
            # If Redis is UP but Celery worker is DOWN,
            # tasks will queue and NOT execute immediately.
            # This is expected Celery behavior.
            from analytics.tasks import log_analytics_task

            log_analytics_task.delay(data)
            return
        except Exception:
            pass
        UserBehaviorEvent.objects.create(
            event_type=event_type,
            user=uid,
            session_id=session_id,
            object_type=object_type,
            object_id=object_id,
            metadata=meta,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception as e:
        logger.debug("Behavior event track_event failed: %s", e, exc_info=False)


def track_content_interaction(
    request=None,
    user=None,
    session_id=None,
    content_type=None,
    content_id=None,
    interaction_type="view",
    dwell_time_ms=None,
    scroll_depth=None,
    position_in_list=None,
    metadata=None,
):
    """
    Phase 14.x: Record detailed content interaction. Never raises; failures are ignored.
    interaction_type: view, click, impression, save, share, like, expand_reviews.
    """
    try:
        if not content_type or content_id is None:
            return
        uid = None
        sid = session_id
        if request:
            uid = getattr(request, "user", None)
            if uid and not uid.is_authenticated:
                uid = None
            if sid is None:
                sid = _get_session_id(request)
        if user is not None:
            uid = user
        UserContentInteraction.objects.create(
            user=uid,
            session_id=sid,
            content_type=content_type[:50],
            content_id=int(content_id),
            interaction_type=interaction_type[:50],
            dwell_time_ms=dwell_time_ms,
            scroll_depth=scroll_depth,
            position_in_list=position_in_list,
            metadata=metadata if metadata is not None else {},
        )
    except Exception as e:
        logger.debug("track_content_interaction failed: %s", e, exc_info=False)


def track_feed_impression(
    request=None,
    user=None,
    session_id=None,
    content_type=None,
    content_id=None,
    feed_type=None,
    feed_position=0,
    was_clicked=False,
    was_booked=False,
):
    """
    Phase 14.x: Record feed impression (what was shown). Never raises; failures are ignored.
    """
    try:
        if not content_type or content_id is None or not feed_type:
            return
        uid = None
        sid = session_id
        if request:
            uid = getattr(request, "user", None)
            if uid and not uid.is_authenticated:
                uid = None
            if sid is None:
                sid = _get_session_id(request)
        if user is not None:
            uid = user
        UserFeedImpression.objects.create(
            user=uid,
            session_id=sid,
            content_type=content_type[:50],
            content_id=int(content_id),
            feed_type=feed_type[:50],
            feed_position=int(feed_position),
            was_clicked=bool(was_clicked),
            was_booked=bool(was_booked),
        )
    except Exception as e:
        logger.debug("track_feed_impression failed: %s", e, exc_info=False)


def track_session_update(
    session_id=None,
    request=None,
    user=None,
    session_start=None,
    session_end=None,
    events_count=0,
    page_views=0,
    search_queries=0,
    total_dwell_time_ms=0,
):
    """
    Phase 14.x: Record or update session analytics. Never raises; failures are ignored.
    """
    try:
        if not session_id:
            if request:
                session_id = _get_session_id(request)
            if not session_id:
                return
        uid = None
        if request:
            uid = getattr(request, "user", None)
            if uid and not uid.is_authenticated:
                uid = None
        if user is not None:
            uid = user
        now = timezone.now()
        start = session_start or now
        end = session_end or now
        UserSessionAnalytics.objects.create(
            session_id=session_id[:120],
            user=uid,
            session_start=start,
            session_end=end,
            events_count=int(events_count),
            page_views=int(page_views),
            search_queries=int(search_queries),
            total_dwell_time_ms=int(total_dwell_time_ms),
        )
    except Exception as e:
        logger.debug("track_session_update failed: %s", e, exc_info=False)


def update_interest_signal(user, interest_type, interest_value, score=0.0):
    """
    Phase 14.x: Upsert aggregated interest signal for a user. Never raises; failures are ignored.
    user must be authenticated. Example: interest_type="pooja_category", interest_value="ganesh_pooja".
    """
    try:
        if not user or not getattr(user, "is_authenticated", True) or not user.is_authenticated:
            return
        if not interest_type or interest_value is None:
            return
        obj, _ = UserInterestSignal.objects.update_or_create(
            user=user,
            interest_type=interest_type[:50],
            interest_value=str(interest_value)[:100],
            defaults={"score": float(score)},
        )
    except Exception as e:
        logger.debug("update_interest_signal failed: %s", e, exc_info=False)
