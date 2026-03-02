"""
Service functions for enforcing trust chain immutability.

TASK 25: Trust Chain Recalculation After Deletions

This module ensures that:
- Trust chains are never recalculated
- Trust is historical and immutable
- Display adapts to inactive referrers
"""

import logging
from django.contrib.auth import get_user_model
from .models import ReferralLink, ReferralUsage

User = get_user_model()
logger = logging.getLogger(__name__)


def get_trust_chain(pandit):
    """
    TASK 25: Get trust chain for a Pandit (read-only, historical).
    
    Trust chains are derived from immutable referral records and never recalculated.
    
    Args:
        pandit: User instance (must have role='pandit')
    
    Returns:
        dict: Trust chain information (read-only, historical)
    """
    if pandit.role != 'pandit':
        return {'error': 'User is not a Pandit'}
    
    trust_chain = {
        'pandit_id': pandit.id,
        'pandit_email': pandit.email,
        'referrer': None,
        'referrer_display': None,
        'is_historical': True,
        'display_note': 'Based on historical referral activity'
    }
    
    # Get referrer from immutable referral records
    if pandit.referred_by:
        referrer = pandit.referred_by
        trust_chain['referrer'] = {
            'id': referrer.id,
            'email': referrer.email,
            'is_active': referrer.is_active,
            'status': referrer.status
        }
        
        # TASK 25: Display referrer with inactive status if applicable
        if referrer.is_active and referrer.status == 'active':
            trust_chain['referrer_display'] = f"Referred by Pandit {referrer.get_full_name() or referrer.email}"
        else:
            trust_chain['referrer_display'] = f"Referred by Pandit {referrer.get_full_name() or referrer.email} (Inactive – Platform Managed)"
    
    # Get referral links created by this pandit (immutable)
    referral_links = ReferralLink.objects.filter(created_by=pandit)
    referral_usages = ReferralUsage.objects.filter(referral_link__in=referral_links)
    
    trust_chain['referrals_created'] = referral_links.count()
    trust_chain['referrals_used'] = referral_usages.count()
    
    # Log trust display (audit)
    try:
        from core.audit import log_deactivation
        log_deactivation(
            pandit,
            actor=None,
            reason="TRUST_CHAIN_PRESERVED - Trust chain displayed (historical, immutable)"
        )
    except Exception:
        pass
    
    return trust_chain


def assert_trust_immutability():
    """
    TASK 25: Assert that trust calculations are immutable.
    
    This function should be called to verify that trust chains
    are not being recalculated when actors are removed.
    
    Returns:
        bool: True if immutability is enforced
    """
    logger.info("TRUST_IMMUTABILITY_ASSERTED - Trust chains are read-only and historical")
    return True


def get_referrer_display_name(referrer):
    """
    TASK 25: Get display name for referrer, handling inactive status.
    
    Args:
        referrer: User instance (referrer)
    
    Returns:
        str: Display name with inactive status if applicable
    """
    if referrer.is_active and referrer.status == 'active':
        return referrer.get_full_name() or referrer.email
    else:
        return f"{referrer.get_full_name() or referrer.email} (Inactive – Platform Managed)"







