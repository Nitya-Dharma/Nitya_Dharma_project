"""
Campaign / AdSet hierarchy serving eligibility.

Invoked only when ENABLE_CAMPAIGNS is True. Does not enforce AdSet targeting,
pricing enforcement, spend accounting, ledger/billing, or delivery intelligence.

Campaign.total_budget vs spent_amount is a serving soft-cap only (no DB writes).
"""

from django.utils import timezone

from .models import Campaign


def is_campaign_serving_eligible(campaign):
    """Return True if Campaign status, schedule, and total-budget soft-cap allow serving."""
    if campaign is None:
        return True
    if str(campaign.status or "").upper() != Campaign.STATUS_ACTIVE:
        return False
    now = timezone.now()
    if campaign.start_date and now < campaign.start_date:
        return False
    if campaign.end_date and now > campaign.end_date:
        return False
    total_budget = campaign.total_budget
    if total_budget is not None and campaign.spent_amount >= total_budget:
        return False
    return True


def is_ad_hierarchy_eligible(ad):
    """
    Return True if linked Campaign/AdSet (if any) allow serving.

    - No Campaign: pass (Advertisement-level rules apply elsewhere).
    - Campaign set: must be ACTIVE, within schedule if set, and under total_budget soft-cap.
    - AdSet set: must have is_active=True.
    """
    campaign = getattr(ad, "campaign", None)
    if campaign is not None and not is_campaign_serving_eligible(campaign):
        return False

    ad_set = getattr(ad, "ad_set", None)
    if ad_set is not None and not bool(ad_set.is_active):
        return False

    return True
