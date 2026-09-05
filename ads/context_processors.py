"""
Context processor for global ad injection into templates.

Slot-based, URL-aware, dashboard-aware, role-aware. Exposes:
- ads: dict of placement/slot -> ad (for dashboard_top, dashboard_sidebar, etc.)
- ads_top, ads_sidebar, ads_footer, ads_in_content: backward compatibility for base template.
"""

from django.conf import settings

from .hierarchy_eligibility import is_ad_hierarchy_eligible
from .models import Advertisement


def active_ads(request):
    ads_qs = Advertisement.objects.filter(is_active=True)
    campaigns_enabled = bool(getattr(settings, "ENABLE_CAMPAIGNS", False))
    if campaigns_enabled:
        ads_qs = ads_qs.select_related("campaign", "ad_set")
    slots = {}

    for ad in ads_qs:
        if campaigns_enabled and not is_ad_hierarchy_eligible(ad):
            continue
        if hasattr(ad, "is_currently_active") and not ad.is_currently_active():
            continue
        if not ad.is_allowed_on_url(request.path):
            continue
        if request.path.startswith("/dashboard/"):
            if not ad.show_on_dashboard:
                continue
        if not ad.is_allowed_for_user(request.user):
            continue
        effective_slots = ad.slots if (getattr(ad, "slots", None) and len(ad.slots)) else ([ad.placement] if getattr(ad, "placement", None) else [])
        for slot in effective_slots:
            slots[slot] = ad

    # Backward compatibility: expose legacy keys for base template
    return {
        "ads": slots,
        "ads_top": slots.get("top"),
        "ads_sidebar": slots.get("sidebar"),
        "ads_footer": slots.get("footer"),
        "ads_in_content": slots.get("in_content"),
    }
