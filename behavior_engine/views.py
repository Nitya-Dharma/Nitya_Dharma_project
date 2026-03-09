"""
Behavior Engine — Safe tracking endpoint.
Uses sendBeacon; fails silently. Does not modify existing analytics.
"""

import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import BehaviorEvent

logger = logging.getLogger(__name__)

# Max request body size (bytes) to prevent abuse; overridable via settings
_DEFAULT_MAX_PAYLOAD = 5000
MAX_PAYLOAD_SIZE = getattr(settings, 'BEHAVIOR_TRACKING_MAX_PAYLOAD_BYTES', _DEFAULT_MAX_PAYLOAD)

# Allowlist: only these event types are stored (prevents junk/injection)
ALLOWED_EVENTS = {
    "page_view",
    "scroll_depth",
    "pandit_card_click",
    "temple_view",
    "follow_click",
    "search_performed",
    "share_click",
}


# SECURITY NOTE: csrf_exempt is intentional here because:
# - This endpoint is used for sendBeacon-style tracking from the browser.
# - Event types are allowlisted (ALLOWED_EVENTS); no sensitive state without validation.
# - Payload size and content-type checks are applied; no direct model field assignment without validation.
# DO NOT remove unless replacing with token-based CSRF strategy.
@csrf_exempt
@require_http_methods(["POST"])
def track_behavior(request):
    if request.method != "POST":
        return JsonResponse({"status": "invalid"}, status=400)

    content_type = request.META.get("CONTENT_TYPE", "").split(";")[0].strip().lower()
    if content_type != "application/json":
        return JsonResponse({"status": "invalid"}, status=400)

    # Payload size protection
    if len(request.body) > MAX_PAYLOAD_SIZE:
        return JsonResponse({"status": "too_large"}, status=413)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"status": "invalid"}, status=400)

    event_type = data.get("event_type") or ""
    if event_type not in ALLOWED_EVENTS:
        return JsonResponse({"status": "ignored"})

    try:
        session_key = (
            request.session.session_key
            if getattr(request, "session", None)
            else None
        ) or ""

        BehaviorEvent.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_id=session_key,
            event_type=event_type,
            entity_type=data.get("entity_type"),
            entity_id=data.get("entity_id"),
            page_url=data.get("page_url", ""),
            page_title=data.get("page_title", ""),
            referrer=data.get("referrer"),
            device_type=data.get("device_type"),
            browser=data.get("browser"),
            os=data.get("os"),
            screen_resolution=data.get("screen_resolution"),
            metadata=data.get("metadata", {}),
        )
    except Exception:
        logger.warning("Behavior tracking save failed", exc_info=True)

    return JsonResponse({"status": "ok"})


# Phase 14: Optional API for frontend to send behavior events (UserBehaviorEvent)
# Phase 14.x: content_view, content_click, feed_impression for advanced behavior (UserContentInteraction, UserFeedImpression)
PHASE14_ALLOWED_EVENTS = {
    "search_query",
    "search_result_click",
    "pandit_profile_view",
    "booking_intent_sent",
    "review_view",
    "page_view",
    "content_view",
    "content_click",
    "feed_impression",
}


def _safe_int(val, default=None):
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


@csrf_exempt
@require_http_methods(["POST"])
def track_event(request):
    """
    Phase 14: POST /behavior/track-event/
    Payload: event_type, object_type, object_id, metadata.
    Phase 14.x: also accepts content_type, content_id, position, scroll_depth, dwell_time_ms,
    feed_type, feed_position, was_clicked, was_booked. Creates UserBehaviorEvent; optionally
    writes to UserContentInteraction and UserFeedImpression. Never raises; allowlisted event types only.
    """
    if request.method != "POST":
        return JsonResponse({"status": "invalid"}, status=400)
    content_type_header = request.META.get("CONTENT_TYPE", "").split(";")[0].strip().lower()
    if content_type_header != "application/json":
        return JsonResponse({"status": "invalid"}, status=400)
    if len(request.body) > MAX_PAYLOAD_SIZE:
        return JsonResponse({"status": "too_large"}, status=413)
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"status": "invalid"}, status=400)
    event_type = (data.get("event_type") or "").strip()
    if event_type not in PHASE14_ALLOWED_EVENTS:
        return JsonResponse({"status": "ignored"})
    try:
        from .services import (
            track_event as svc_track_event,
            track_content_interaction,
            track_feed_impression,
        )
        obj_id = data.get("object_id")
        if obj_id is not None:
            obj_id = _safe_int(obj_id)
        object_type = (data.get("object_type") or "").strip() or None
        if object_type is None and data.get("content_type"):
            object_type = (data.get("content_type") or "").strip()[:50] or None
        if obj_id is None and data.get("content_id") is not None:
            obj_id = _safe_int(data.get("content_id"))
        svc_track_event(
            event_type=event_type,
            request=request,
            object_type=object_type,
            object_id=obj_id,
            metadata=data.get("metadata") or {},
        )
        # Phase 14.x: write to UserContentInteraction when content_type + content_id present
        ct = (data.get("content_type") or "").strip()[:50]
        cid = _safe_int(data.get("content_id"))
        if ct and cid is not None:
            interaction_map = {
                "content_view": "view",
                "content_click": "click",
                "feed_impression": "impression",
            }
            interaction_type = interaction_map.get(event_type, "view")
            track_content_interaction(
                request=request,
                content_type=ct,
                content_id=cid,
                interaction_type=interaction_type,
                dwell_time_ms=_safe_int(data.get("dwell_time_ms")),
                scroll_depth=_safe_int(data.get("scroll_depth")),
                position_in_list=_safe_int(data.get("position")),
                metadata=data.get("metadata") or {},
            )
        # Phase 14.x: write to UserFeedImpression when feed_type + feed_position (and content) present
        feed_type = (data.get("feed_type") or "").strip()[:50]
        feed_pos = _safe_int(data.get("feed_position"), 0)
        if feed_type and (ct or data.get("content_type")) and (cid is not None or data.get("content_id") is not None):
            if not ct:
                ct = (data.get("content_type") or "").strip()[:50]
            if cid is None:
                cid = _safe_int(data.get("content_id"), 0)
            track_feed_impression(
                request=request,
                content_type=ct or "unknown",
                content_id=cid,
                feed_type=feed_type,
                feed_position=feed_pos,
                was_clicked=bool(data.get("was_clicked", False)),
                was_booked=bool(data.get("was_booked", False)),
            )
    except Exception:
        logger.debug("Phase 14/14.x track_event save failed", exc_info=False)
    return JsonResponse({"status": "ok"})
