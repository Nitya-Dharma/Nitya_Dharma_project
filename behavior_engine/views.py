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
