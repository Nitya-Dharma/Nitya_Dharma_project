"""
Advertisement analytics: click tracking redirect and dashboard views.

Records AdClick then redirects to the ad's target URL. Does not modify ad serving.
Dashboard views are read-only and use dashboard_service for all metrics.
"""

from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse, Http404
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt

from ads.models import Advertisement
from .protection import should_skip_tracking
from .services import record_ad_click, record_ad_impression, store_last_click_attribution
from .services.dashboard_service import (
    get_advertiser_campaign_metrics,
    get_pandit_ad_analytics,
    get_platform_ad_analytics,
    get_hourly_impression_chart_data,
    get_weekday_chart_data,
    get_monthly_trend_chart_data,
    get_city_performance,
    get_placement_chart_data,
    get_ad_conversion_funnel,
    get_funnel_chart_data,
    get_device_distribution,
    get_user_type_distribution,
    get_revenue_summary,
)


def _superuser_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise Http404()
        return view_func(request, *args, **kwargs)
    return _wrapped


def _trusted_ad_redirect_fallback(ad) -> str:
    """Super Admin-stored advertiser URL, or site root when unset."""
    stored = (getattr(ad, "redirect_url", None) or "").strip()
    return stored or "/"


def _click_redirect_target(request, ad) -> str:
    """
    Resolve the click redirect destination.

    Query-string ``redirect=`` is attacker-controlled: only same-origin /
    relative URLs are accepted via Django's url_has_allowed_host_and_scheme.
    Unsafe query values fall back to Advertisement.redirect_url (trusted
    Super Admin destination, which may be external) or "/".
    """
    fallback = _trusted_ad_redirect_fallback(ad)
    raw = request.GET.get("redirect")
    if raw is None:
        return fallback
    candidate = str(raw).strip()
    if not candidate:
        return fallback
    allowed_hosts = {request.get_host()}
    if url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts=allowed_hosts,
        require_https=False,
    ):
        return candidate
    return fallback


@require_GET
@csrf_exempt
@xframe_options_exempt
def track_click(request, ad_id: int):
    """
    Record an ad click and redirect to the advertiser URL.
    Query params: redirect (required, target URL), placement (slot), page_type.
    Phase-3: bot filtering, rate limiting, and placement validation; invalid/abuse requests
    still get normal redirect response but no event is recorded.
    """
    ad = get_object_or_404(Advertisement, pk=ad_id)
    placement = (request.GET.get("placement") or "").strip()
    target = _click_redirect_target(request, ad)

    skip, _reason = should_skip_tracking(request, ad_id, placement, is_impression=False)
    if not skip:
        page_type = request.GET.get("page_type", "")
        user_id = request.user.pk if request.user.is_authenticated else None
        pandit_id = (
            int(request.GET["pandit_id"])
            if request.GET.get("pandit_id", "").isdigit()
            else None
        )
        record_ad_click(
            ad_id=ad_id,
            placement_position=placement or (ad.slots[0] if getattr(ad, "slots", None) else ad.placement),
            page_type=page_type,
            campaign_id=str(ad.campaign_id) if ad.campaign_id is not None else None,
            user_id=user_id,
            pandit_id=pandit_id,
            request=request,
        )
        store_last_click_attribution(
            request,
            ad_id,
            campaign_id=str(ad.campaign_id) if ad.campaign_id is not None else None,
        )
        # Batch E: direct allowlisted WhatsApp destination → existing contact-intent/lead.
        # Uses final resolved target only; requires session attribution just stored above.
        if _is_allowed_whatsapp_redirect(target):
            try:
                from .services.attribution_bridge import (
                    record_whatsapp_contact_from_session,
                )

                record_whatsapp_contact_from_session(
                    request,
                    user_id=user_id,
                    pandit_id=pandit_id,
                )
            except Exception:
                pass

    # Batch A: enrich allowlisted WhatsApp destinations only (after safe resolve).
    if _is_allowed_whatsapp_redirect(target):
        try:
            from profiles.whatsapp_ad_prefill import (
                apply_whatsapp_text_param,
                build_ad_attributed_whatsapp_message,
            )

            message = build_ad_attributed_whatsapp_message(
                ad_id=ad.pk,
                campaign_id=(
                    str(ad.campaign_id) if ad.campaign_id is not None else None
                ),
            )
            if message:
                target = apply_whatsapp_text_param(target, message)
        except Exception:
            pass

    return redirect(target)


_ALLOWED_WHATSAPP_HOSTS = frozenset({"wa.me", "api.whatsapp.com"})


def _is_allowed_whatsapp_redirect(url: str) -> bool:
    """Strict allowlist: https only, wa.me or api.whatsapp.com, no userinfo."""
    from urllib.parse import urlparse

    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    if parsed.scheme != "https":
        return False
    if parsed.username or parsed.password:
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname in _ALLOWED_WHATSAPP_HOSTS


@require_GET
@csrf_exempt
@xframe_options_exempt
def track_whatsapp_redirect(request):
    """
    Record WhatsApp CTA contact intent (CONVERSION_OTHER) when ad attribution exists,
    then redirect to the validated original wa.me / api.whatsapp.com URL unchanged.
    """
    target = (request.GET.get("redirect") or "").strip()
    if not _is_allowed_whatsapp_redirect(target):
        return redirect("/")

    pandit_id = None
    if request.GET.get("pandit_id", "").isdigit():
        pandit_id = int(request.GET["pandit_id"])

    try:
        from .services.attribution_bridge import record_whatsapp_contact_from_session

        record_whatsapp_contact_from_session(
            request,
            user_id=request.user.pk if request.user.is_authenticated else None,
            pandit_id=pandit_id,
        )
    except Exception:
        pass

    return redirect(target)


@require_GET
@csrf_exempt
@xframe_options_exempt
def track_impression(request, ad_id: int):
    """
    Record one ad impression when the ad is viewed in the browser (call from client when ad enters viewport).
    Query params: placement (slot), page_type (optional). Request context (user, session, referrer, etc.) is used.
    Returns 204 No Content so the browser can use it as a tracking pixel or fetch.
    Phase-3: bot filtering, rate limiting, placement validation, and backend duplicate-impression
    guard; skipped requests still get 204 so frontend behavior is unchanged.
    """
    from django.http import HttpResponse

    ad = get_object_or_404(Advertisement, pk=ad_id)
    placement = (request.GET.get("placement") or "").strip()

    skip, _reason = should_skip_tracking(request, ad_id, placement, is_impression=True)
    if not skip:
        page_type = request.GET.get("page_type", "")
        user_id = request.user.pk if request.user.is_authenticated else None
        pandit_id = None
        if request.GET.get("pandit_id", "").isdigit():
            pandit_id = int(request.GET["pandit_id"])
        record_ad_impression(
            ad_id=ad_id,
            placement_position=placement or (getattr(ad, "placement", None) or "unknown"),
            page_type=page_type,
            campaign_id=str(ad.campaign_id) if ad.campaign_id is not None else None,
            user_id=user_id,
            pandit_id=pandit_id,
            request=request,
        )
    return HttpResponse(status=204)


# --- Dashboard views (Phase 9–10): read-only analytics ---
#
# Context contract for advertiser_dashboard.html (keep in sync for future-proofing):
#   ad              → ads.models.Advertisement (from get_object_or_404)
#   metrics         → get_advertiser_campaign_metrics (dict: days, start, end, total_impressions, total_clicks, ctr, top_placements)
#   city_performance→ get_city_performance (list of dicts)
#   funnel          → get_ad_conversion_funnel (dict: impressions, clicks, profile_views, booking_intents, *_rate)
#   device_distribution, user_type_distribution → lists from dashboard_service
#   revenue_summary → get_revenue_summary (dict: total_revenue, total_impressions, total_clicks)
#   chart_data      → { daily: {labels, data}, funnel: {labels, data}, device: {labels, data} } for ads_analytics.js
#   dashboard_has_data → True so dashboard_base always shows content (GA4-style layout)
# All data comes from ads_analytics.models (AdImpression, AdClick, AdConversionIntent, AdRevenueEvent) via dashboard_service.


def _empty_advertiser_context(ad, days: int):
    """Fallback context when dashboard_service raises (DB error, etc.). Ensures page still renders with zeros."""
    from datetime import date, timedelta
    from django.utils import timezone
    end = timezone.now().date()
    start = end - timedelta(days=days)
    return {
        "metrics": {
            "ad_id": ad.pk,
            "days": days,
            "start": start,
            "end": end,
            "total_impressions": 0,
            "total_clicks": 0,
            "ctr": 0.0,
            "top_placements": [],
        },
        "hourly_chart": {"labels": [], "data": []},
        "weekday_chart": {"labels": [], "impressions": [], "clicks": []},
        "monthly_chart": {"labels": [], "impressions": [], "clicks": []},
        "city_performance": [],
        "funnel": {
            "impressions": 0,
            "clicks": 0,
            "profile_views": 0,
            "booking_intents": 0,
            "click_rate": 0.0,
            "profile_view_rate": 0.0,
            "booking_intent_rate": 0.0,
        },
        "funnel_chart": {"labels": [], "data": []},
        "device_distribution": [],
        "user_type_distribution": [
            {"user_type": "guest", "impressions": 0, "clicks": 0},
            {"user_type": "registered", "impressions": 0, "clicks": 0},
        ],
        "revenue_summary": {"total_revenue": 0.0, "total_impressions": 0, "total_clicks": 0},
    }


@_superuser_required
@require_GET
def advertiser_dashboard_view(request, ad_id: int):
    """Advertiser/campaign dashboard: metrics, time, location, funnel, device, revenue.
    Read-only: all data from dashboard_service → AdImpression, AdClick, AdConversionIntent, AdRevenueEvent.
    On service/DB failure returns empty-but-valid context so the dashboard still renders (GA4-style with zeros).
    """
    ad = get_object_or_404(Advertisement, pk=ad_id)
    days = max(1, min(365, int(request.GET.get("days", 30))))

    try:
        metrics = get_advertiser_campaign_metrics(ad_id, days=days)
        hourly_chart = get_hourly_impression_chart_data(ad_id, days=min(days, 7))
        weekday_chart = get_weekday_chart_data(ad_id, days=days)
        monthly_chart = get_monthly_trend_chart_data(ad_id, months=6)
        city_performance = get_city_performance(ad_id, days=days)
        funnel = get_ad_conversion_funnel(ad_id, days=days)
        funnel_chart = get_funnel_chart_data(ad_id, days=days)
        device_dist = get_device_distribution(ad_id, days=days)
        user_type_dist = get_user_type_distribution(ad_id, days=days)
        revenue_summary = get_revenue_summary(ad_id=ad_id, days=days)
    except Exception:
        empty = _empty_advertiser_context(ad, days)
        metrics = empty["metrics"]
        hourly_chart = empty["hourly_chart"]
        weekday_chart = empty["weekday_chart"]
        monthly_chart = empty["monthly_chart"]
        city_performance = empty["city_performance"]
        funnel = empty["funnel"]
        funnel_chart = empty["funnel_chart"]
        device_dist = empty["device_distribution"]
        user_type_dist = empty["user_type_distribution"]
        revenue_summary = empty["revenue_summary"]

    # Normalize to lists so template never sees None
    device_dist = list(device_dist) if device_dist is not None else []
    user_type_dist = list(user_type_dist) if user_type_dist is not None else []
    city_performance = list(city_performance) if city_performance is not None else []

    if request.headers.get("Accept") == "application/json":
        return JsonResponse({
            "metrics": metrics,
            "charts": {
                "hourly": hourly_chart,
                "weekday": weekday_chart,
                "monthly": monthly_chart,
                "funnel": funnel_chart,
            },
            "city_performance": city_performance,
            "funnel": funnel,
            "device_distribution": device_dist,
            "user_type_distribution": user_type_dist,
            "revenue_summary": revenue_summary,
        })
    # Chart-ready payload for template (GA4-style): always dicts with labels + data for ads_analytics.js
    hourly_chart = hourly_chart or {}
    funnel_chart = funnel_chart or {}
    device_chart = {
        "labels": [d.get("device_type") or "unknown" for d in device_dist],
        "data": [d.get("impressions", 0) for d in device_dist],
    }
    chart_data = {
        "daily": {"labels": hourly_chart.get("labels") or [], "data": hourly_chart.get("data") or []},
        "funnel": {"labels": funnel_chart.get("labels") or [], "data": funnel_chart.get("data") or []},
        "device": device_chart,
    }
    return _render(
        request,
        "ads_analytics/advertiser_dashboard.html",
        {
            "ad": ad,
            "metrics": metrics,
            "hourly_chart": hourly_chart,
            "weekday_chart": weekday_chart,
            "monthly_chart": monthly_chart,
            "city_performance": city_performance,
            "funnel": funnel,
            "funnel_chart": funnel_chart,
            "device_distribution": device_dist,
            "user_type_distribution": user_type_dist,
            "revenue_summary": revenue_summary,
            "chart_data": chart_data,
            "dashboard_has_data": True,  # Always render GA4-style dashboard layout (metrics, charts, filters)
        },
    )


def _render(request, template_name, context):
    return render(request, template_name, context)


@_superuser_required
@require_GET
def pandit_ad_dashboard_view(request, pandit_id: int):
    """Pandit profile ad analytics: impressions/clicks on profile, top ads."""
    days = int(request.GET.get("days", 30))
    analytics = get_pandit_ad_analytics(pandit_id, days=days)
    if request.headers.get("Accept") == "application/json":
        return JsonResponse(analytics)
    return _render(request, "ads_analytics/pandit_ad_dashboard.html", {"pandit_id": pandit_id, "analytics": analytics})


def _empty_platform_context(days: int):
    """Fallback when platform analytics fails; keeps GA4-style layout with zeros."""
    from datetime import date, timedelta
    from django.utils import timezone
    end = timezone.now().date()
    start = end - timedelta(days=days)
    return {
        "platform": {
            "days": days,
            "start": start,
            "end": end,
            "total_impressions": 0,
            "total_clicks": 0,
            "platform_ctr": 0.0,
            "placement_performance": [],
            "top_cities": [],
            "top_campaigns": [],
        },
        "placement_chart": {
            "placements": [],
            "impressions": [],
            "clicks": [],
            "ctr_values": [],
        },
    }


@_superuser_required
@require_GET
def admin_ad_intelligence_view(request):
    """Platform-level ad intelligence: totals, placement performance, top cities/campaigns.
    Always renders GA4-style layout (cards, charts, filters) with 0 values when data is empty."""
    days = max(1, min(365, int(request.GET.get("days", 30))))
    try:
        platform = get_platform_ad_analytics(days=days)
        placement_chart = get_placement_chart_data(days=days)
    except Exception:
        empty = _empty_platform_context(days)
        platform = empty["platform"]
        placement_chart = empty["placement_chart"]
    platform = platform or _empty_platform_context(days)["platform"]
    placement_chart = placement_chart or _empty_platform_context(days)["placement_chart"]
    placement_chart.setdefault("placements", [])
    placement_chart.setdefault("impressions", [])
    placement_chart.setdefault("clicks", [])
    placement_chart.setdefault("ctr_values", [])

    if request.headers.get("Accept") == "application/json":
        return JsonResponse({
            "platform": platform,
            "placement_chart": placement_chart,
        })
    return _render(request, "ads_analytics/admin_ad_intelligence.html", {
        "platform": platform,
        "placement_chart": placement_chart,
        "dashboard_has_data": True,
    })
