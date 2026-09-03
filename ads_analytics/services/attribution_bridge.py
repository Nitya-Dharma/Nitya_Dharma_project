"""
Minimal session bridge: last AdClick → downstream booking conversion.

Reuses existing AdClick (via track_click) and AdConversionIntent recording.
No new models or migrations.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.http import HttpRequest

logger = logging.getLogger(__name__)

SESSION_KEY = "ads_last_click_attribution"


def store_last_click_attribution(request: Optional[HttpRequest], ad_id: int) -> None:
    """Persist last-click ad identity in session (survives login cycle_key)."""
    if not request or not hasattr(request, "session") or ad_id is None:
        return
    try:
        request.session[SESSION_KEY] = {"ad_id": int(ad_id)}
        request.session.modified = True
    except Exception as exc:
        logger.warning("store_last_click_attribution failed: ad_id=%s %s", ad_id, exc)


def record_booking_conversion_from_session(
    request: Optional[HttpRequest],
    *,
    user_id: Optional[int] = None,
    pandit_id: Optional[int] = None,
) -> bool:
    """
    If session holds a prior ad click, record AdConversionIntent (booking_intent)
    and clear the session payload. Failures must not break booking flows.
    """
    if not request or not hasattr(request, "session"):
        return False
    payload = request.session.get(SESSION_KEY)
    if not isinstance(payload, dict):
        return False
    raw_ad_id = payload.get("ad_id")
    if raw_ad_id is None:
        return False
    try:
        ad_id = int(raw_ad_id)
    except (TypeError, ValueError):
        return False

    from ads_analytics.models import AdConversionIntent
    from ads_analytics.services.event_recording import record_ad_conversion_intent

    ok = record_ad_conversion_intent(
        ad_id=ad_id,
        conversion_type=AdConversionIntent.CONVERSION_BOOKING_INTENT,
        user_id=user_id,
        pandit_id=pandit_id,
    )
    if ok:
        try:
            del request.session[SESSION_KEY]
            request.session.modified = True
        except Exception:
            pass
    return ok


def record_whatsapp_contact_from_session(
    request: Optional[HttpRequest],
    *,
    user_id: Optional[int] = None,
    pandit_id: Optional[int] = None,
) -> bool:
    """
    If session holds a prior ad click, record AdConversionIntent (other / WhatsApp CTA).
    Does NOT clear session — booking attribution may follow later (Phase-2A).
    """
    if not request or not hasattr(request, "session"):
        return False
    payload = request.session.get(SESSION_KEY)
    if not isinstance(payload, dict):
        return False
    raw_ad_id = payload.get("ad_id")
    if raw_ad_id is None:
        return False
    try:
        ad_id = int(raw_ad_id)
    except (TypeError, ValueError):
        return False

    from ads_analytics.models import AdConversionIntent
    from ads_analytics.services.event_recording import record_ad_conversion_intent

    safe_pandit_id = pandit_id
    if safe_pandit_id is not None:
        try:
            from django.contrib.auth import get_user_model

            if not get_user_model().objects.filter(pk=safe_pandit_id, role="pandit").exists():
                safe_pandit_id = None
        except Exception:
            safe_pandit_id = None

    return record_ad_conversion_intent(
        ad_id=ad_id,
        conversion_type=AdConversionIntent.CONVERSION_OTHER,
        user_id=user_id,
        pandit_id=safe_pandit_id,
    )
