"""
Campaign / AdSet hierarchy serving eligibility.

Invoked only when ENABLE_CAMPAIGNS is True. Does not enforce AdSet targeting,
pricing, spend, or delivery intelligence.
"""

from django.utils import timezone

from .models import Campaign


def is_campaign_serving_eligible(campaign):
    """Return True if Campaign status is ACTIVE and within optional schedule."""
    if campaign is None:
        return True
    if str(campaign.status or "").upper() != Campaign.STATUS_ACTIVE:
        return False
    now = timezone.now()
    if campaign.start_date and now < campaign.start_date:
        return False
    if campaign.end_date and now > campaign.end_date:
        return False
    return True


def is_ad_hierarchy_eligible(ad):
    """
    Return True if linked Campaign/AdSet (if any) allow serving.

    - No Campaign: pass (Advertisement-level rules apply elsewhere).
    - Campaign set: must be ACTIVE and within Campaign start/end if set.
    - AdSet set: must have is_active=True.
    """
    campaign = getattr(ad, "campaign", None)
    if campaign is not None and not is_campaign_serving_eligible(campaign):
        return False

    ad_set = getattr(ad, "ad_set", None)
    if ad_set is not None and not bool(ad_set.is_active):
        return False

    return True
