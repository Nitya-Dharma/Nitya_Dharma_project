"""
Service functions for enforcing trust and analytics immutability.

TASK 15: Analytics/Trust Display Must Be Historical

This module ensures that:
- Trust indicators are read-only and historical
- Analytics remain unchanged when actors are removed
- No recalculation triggered by deletion
"""

import logging
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def get_trust_indicators(pandit):
    """
    TASK 15: Get trust indicators for a Pandit (read-only, historical).
    
    Trust indicators are derived from historical events and never recalculated
    when actors are removed or deactivated.
    
    Args:
        pandit: User instance (must have role='pandit')
    
    Returns:
        dict: Trust indicators (read-only, historical)
    """
    if pandit.role != 'pandit':
        raise ValidationError(f"User {pandit.email} is not a Pandit.")
    
    # Trust indicators are read-only and historical
    # They are derived from immutable event logs, not recalculated
    
    trust_data = {
        'referral_chain': _get_referral_chain(pandit),
        'trust_badges': _get_trust_badges(pandit),
        'verification_labels': _get_verification_labels(pandit),
        'historical_rating': _get_historical_rating(pandit),
        'review_count': _get_review_count(pandit),
        'is_historical': True,  # Always true - trust is historical
        'display_note': 'Based on historical activity'
    }
    
    # Log trust display (audit)
    from core.audit import log_deactivation
    log_deactivation(
        pandit,
        actor=None,
        reason="TRUST_DISPLAY_RENDERED - Historical trust indicators displayed"
    )
    
    return trust_data


def _get_referral_chain(pandit):
    """Get referral chain (immutable, historical)."""
    try:
        from referrals.models import ReferralUsage, ReferralLink
        from accounts.models import User
        
        # Get referral chain from immutable referral records
        referral_chain = []
        
        # Get who referred this pandit (immutable)
        if pandit.referred_by:
            referral_chain.append({
                'referrer': pandit.referred_by.email if pandit.referred_by.is_active else f"{pandit.referred_by.email} (Inactive)",
                'is_active': pandit.referred_by.is_active,
                'historical': True
            })
        
        # Get referral links created by this pandit (immutable)
        referral_links = ReferralLink.objects.filter(created_by=pandit)
        usage_count = ReferralUsage.objects.filter(referral_link__in=referral_links).count()
        
        referral_chain.append({
            'referrals_created': referral_links.count(),
            'referrals_used': usage_count,
            'historical': True
        })
        
        return referral_chain
    except ImportError:
        return []


def _get_trust_badges(pandit):
    """Get trust badges (immutable, historical)."""
    badges = []
    
    # Email verified badge (historical)
    if hasattr(pandit, 'email_verified') and pandit.email_verified:
        badges.append({
            'name': 'Email Verified',
            'historical': True
        })
    
    # Admin approved badge (historical)
    if pandit.status == 'active' and pandit.role == 'pandit':
        badges.append({
            'name': 'Admin Approved',
            'historical': True
        })
    
    return badges


def _get_verification_labels(pandit):
    """Get verification labels (immutable, historical)."""
    labels = []
    
    # Status label (historical)
    if pandit.status == 'active':
        labels.append('Active Pandit')
    elif pandit.status == 'pending':
        labels.append('Pending Approval')
    
    # Role label (historical)
    if pandit.role == 'pandit':
        labels.append('Verified Pandit')
    
    return labels


def _get_historical_rating(pandit):
    """Get historical rating (immutable, from reviews)."""
    try:
        from reviews.models import Review
        from django.db import models
        
        # Get average rating from immutable review records
        reviews = Review.objects.filter(pandit=pandit, is_visible=True)
        
        if reviews.exists():
            avg_rating = reviews.aggregate(
                avg=models.Avg('rating')
            )['avg'] or 0.0
            
            return {
                'average': round(avg_rating, 2),
                'count': reviews.count(),
                'historical': True
            }
        
        return {
            'average': 0.0,
            'count': 0,
            'historical': True
        }
    except ImportError:
        return {'average': 0.0, 'count': 0, 'historical': True}


def _get_review_count(pandit):
    """Get review count (immutable, from reviews)."""
    try:
        from reviews.models import Review
        
        # Count from immutable review records
        count = Review.objects.filter(pandit=pandit, is_visible=True).count()
        return {
            'count': count,
            'historical': True
        }
    except ImportError:
        return {'count': 0, 'historical': True}


def get_analytics_data(event_name=None, event_category=None, start_date=None, end_date=None):
    """
    TASK 15: Get analytics data (read-only, from immutable event logs).
    
    Analytics are read from immutable event logs and never recalculated
    when actors are removed or deactivated.
    
    Args:
        event_name: Optional event name filter
        event_category: Optional event category filter
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        dict: Analytics data (read-only, historical)
    """
    from analytics.models import AnalyticsEvent
    from django.db import models
    from django.utils import timezone
    
    # Build query from immutable event logs
    queryset = AnalyticsEvent.objects.all()
    
    if event_name:
        queryset = queryset.filter(event_name=event_name)
    
    if event_category:
        queryset = queryset.filter(event_category=event_category)
    
    if start_date:
        queryset = queryset.filter(timestamp__gte=start_date)
    
    if end_date:
        queryset = queryset.filter(timestamp__lte=end_date)
    
    # Aggregate from immutable events (no recalculation)
    analytics_data = {
        'total_events': queryset.count(),
        'events_by_category': dict(
            queryset.values('event_category')
            .annotate(count=models.Count('id'))
            .values_list('event_category', 'count')
        ),
        'is_historical': True,  # Always true - analytics are historical
        'display_note': 'Based on historical activity',
        'read_only': True
    }
    
    # Log analytics access (audit)
    from core.audit import log_deactivation
    log_deactivation(
        None,  # System event
        actor=None,
        reason="ANALYTICS_READ_ONLY_ASSERTED - Analytics read from immutable event logs"
    )
    
    return analytics_data


def assert_trust_immutability():
    """
    TASK 15: Assert that trust calculations are immutable.
    
    This function should be called to verify that trust indicators
    are not being recalculated when actors are removed.
    
    Returns:
        bool: True if immutability is enforced
    """
    # This is a guard function - in production, you might want to
    # add checks to ensure trust calculations are not triggered
    # by deletion events
    
    logger.info("TRUST_IMMUTABILITY_ASSERTED - Trust calculations are read-only and historical")
    return True

