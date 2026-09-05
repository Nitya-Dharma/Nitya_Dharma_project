"""
Lightweight advertisement event recording and revenue logging.

Used by templates/views to record impressions and clicks without slowing
page render. Single insert per call; no heavy joins. Safe for production.
"""

import logging
from typing import Optional, Dict, Any

from django.http import HttpRequest

logger = logging.getLogger(__name__)

# Truncate long values to stay within model max lengths
PAGE_URL_MAX = 2048
REFERRER_MAX = 500
LOCATION_MAX = 150
PAGE_TYPE_MAX = 50
PLACEMENT_MAX = 50
DEVICE_MAX = 20


def _truncate(s: Optional[str], max_len: int) -> str:
    if s is None:
        return ""
    return (s[: max_len - 3] + "...") if len(s) > max_len else s


def _get_device_type(request: Optional[HttpRequest]) -> str:
    """
    Classify device from User-Agent for consistent reporting across desktop, mobile, tablet.
    Covers: iPhone, iPod, Android phones, Android tablets, iPad, generic mobile/tablet.
    """
    if not request:
        return ""
    ua = request.META.get("HTTP_USER_AGENT") or ""
    ua_lower = ua.lower()
    # Tablet first (iPad, Android tablets often omit "mobile")
    if "ipad" in ua_lower or "tablet" in ua_lower:
        return "tablet"
    if "android" in ua_lower and "mobile" not in ua_lower:
        return "tablet"
    # Mobile phones: iPhone, iPod, Android with Mobile, generic "mobile"
    if "iphone" in ua_lower or "ipod" in ua_lower:
        return "mobile"
    if "mobile" in ua_lower and "tablet" not in ua_lower:
        return "mobile"
    if "android" in ua_lower:
        return "mobile"
    return "desktop"


def _location_from_request(request: Optional[HttpRequest]) -> Dict[str, str]:
    """Derive location from request (user profile, session, or empty). No PII."""
    out = {
        "viewer_city": "",
        "viewer_area": "",
        "viewer_state": "",
        "viewer_country": "",
    }
    if not request:
        return out
    # Optional: from session (e.g. set by geo middleware)
    for key in ["viewer_city", "viewer_area", "viewer_state", "viewer_country"]:
        val = request.session.get(key)
        if val and isinstance(val, str):
            out[key] = _truncate(val, LOCATION_MAX)
    # Optional: from user profile if available (non-PII city/state only)
    user = getattr(request, "user", None)
    if user and user.is_authenticated and hasattr(user, "profile"):
        try:
            profile = user.profile
            if getattr(profile, "city", None):
                out["viewer_city"] = _truncate(str(profile.city), LOCATION_MAX)
            if getattr(profile, "state", None):
                out["viewer_state"] = _truncate(str(profile.state), LOCATION_MAX)
            if getattr(profile, "country", None):
                out["viewer_country"] = _truncate(str(profile.country), LOCATION_MAX)
        except Exception:
            pass
    return out


def record_ad_impression(
    ad_id: int,
    placement_position: str,
    *,
    campaign_id: Optional[str] = None,
    page_type: str = "",
    page_url: str = "",
    user_id: Optional[int] = None,
    pandit_id: Optional[int] = None,
    session_id: str = "",
    device_type: str = "",
    location_data: Optional[Dict[str, str]] = None,
    referrer_source: str = "",
    request: Optional[HttpRequest] = None,
) -> bool:
    """
    Create one AdImpression record. Call when an ad is rendered.

    Kept minimal for speed: single INSERT, no SELECTs. Run in request context
    or defer to background task if needed.
    """
    from ads_analytics.models import AdImpression
    from ads.models import Advertisement

    try:
        ad = Advertisement.objects.filter(pk=ad_id).first()
        if not ad:
            return False
        loc = location_data or _location_from_request(request)
        if request and not session_id:
            session_id = getattr(request.session, "session_key", "") or ""
        if request and not device_type:
            device_type = _get_device_type(request)
        if request and not referrer_source:
            referrer_source = _truncate(request.META.get("HTTP_REFERER") or "", REFERRER_MAX)
        if request and not page_url:
            page_url = _truncate(request.build_absolute_uri() or "", PAGE_URL_MAX)

        AdImpression.objects.create(
            ad_id=ad_id,
            campaign_id=_truncate(campaign_id, 100) if campaign_id else None,
            placement_position=_truncate(placement_position, PLACEMENT_MAX),
            page_type=_truncate(page_type, PAGE_TYPE_MAX),
            page_url=_truncate(page_url, PAGE_URL_MAX),
            user_id=user_id,
            pandit_id=pandit_id,
            session_id=_truncate(session_id, 40),
            device_type=_truncate(device_type, DEVICE_MAX),
            viewer_city=loc.get("viewer_city", "")[:LOCATION_MAX],
            viewer_area=loc.get("viewer_area", "")[:LOCATION_MAX],
            viewer_state=loc.get("viewer_state", "")[:LOCATION_MAX],
            viewer_country=loc.get("viewer_country", "")[:LOCATION_MAX],
            referrer_source=_truncate(referrer_source, REFERRER_MAX),
        )
        return True
    except Exception as e:
        logger.warning("record_ad_impression failed: ad_id=%s %s", ad_id, e)
        return False


def record_ad_click(
    ad_id: int,
    placement_position: str,
    *,
    campaign_id: Optional[str] = None,
    page_type: str = "",
    user_id: Optional[int] = None,
    pandit_id: Optional[int] = None,
    session_id: str = "",
    location_data: Optional[Dict[str, str]] = None,
    referrer_source: str = "",
    request: Optional[HttpRequest] = None,
) -> bool:
    """
    Create one AdClick record. Call when user clicks an ad (e.g. in redirect view).
    """
    from ads_analytics.models import AdClick
    from ads.models import Advertisement

    try:
        ad = Advertisement.objects.filter(pk=ad_id).first()
        if not ad:
            return False
        loc = location_data or _location_from_request(request)
        if request and not session_id:
            session_id = getattr(request.session, "session_key", "") or ""
        if request and not referrer_source:
            referrer_source = _truncate(request.META.get("HTTP_REFERER") or "", REFERRER_MAX)

        AdClick.objects.create(
            ad_id=ad_id,
            campaign_id=_truncate(campaign_id, 100) if campaign_id else None,
            placement_position=_truncate(placement_position, PLACEMENT_MAX),
            page_type=_truncate(page_type, PAGE_TYPE_MAX),
            user_id=user_id,
            pandit_id=pandit_id,
            session_id=_truncate(session_id, 40),
            viewer_city=loc.get("viewer_city", "")[:LOCATION_MAX],
            viewer_area=loc.get("viewer_area", "")[:LOCATION_MAX],
            viewer_state=loc.get("viewer_state", "")[:LOCATION_MAX],
            viewer_country=loc.get("viewer_country", "")[:LOCATION_MAX],
            referrer_source=_truncate(referrer_source, REFERRER_MAX),
        )
        return True
    except Exception as e:
        logger.warning("record_ad_click failed: ad_id=%s %s", ad_id, e)
        return False


def record_ad_revenue_event(
    ad_id: Optional[int],
    billing_model: str,
    *,
    impressions: int = 0,
    clicks: int = 0,
    revenue_amount: float,
) -> bool:
    """
    Record a revenue event (CPM/CPC/Sponsored/Featured).
    Call from billing or aggregation; does not modify ad serving.
    """
    from decimal import Decimal
    from ads_analytics.models import AdRevenueEvent

    try:
        AdRevenueEvent.objects.create(
            ad_id=ad_id,
            billing_model=billing_model,
            impressions=impressions,
            clicks=clicks,
            revenue_amount=Decimal(str(revenue_amount)),
        )
        return True
    except Exception as e:
        logger.warning("record_ad_revenue_event failed: %s", e)
        return False


def record_ad_conversion_intent(
    ad_id: int,
    conversion_type: str,
    *,
    user_id: Optional[int] = None,
    pandit_id: Optional[int] = None,
    campaign_id: Optional[str] = None,
) -> bool:
    """Record a conversion intent (e.g. booking_intent) for attribution."""
    from ads_analytics.models import AdConversionIntent
    from ads.models import Advertisement

    try:
        if not Advertisement.objects.filter(pk=ad_id).exists():
            return False
        AdConversionIntent.objects.create(
            ad_id=ad_id,
            user_id=user_id,
            pandit_id=pandit_id,
            conversion_type=conversion_type,
            campaign_id=_truncate(campaign_id, 100) if campaign_id else None,
        )
        return True
    except Exception as e:
        logger.warning("record_ad_conversion_intent failed: ad_id=%s %s", ad_id, e)
        return False
