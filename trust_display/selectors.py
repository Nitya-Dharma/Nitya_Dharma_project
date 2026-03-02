"""
Trust Display Selectors

Task 10.16: Trust Data Selectors

Read-only data selectors for trust display.
NO computation, NO mutation, NO business logic.
Only data retrieval and aggregation.
"""

from typing import Dict, Any, List, Optional
from django.contrib.auth import get_user_model
from profiles.models import PanditProfile
from reviews.models import Review
from reviews.services import ReviewService

User = get_user_model()


def get_referral_chain_for_pandit(pandit: User) -> Dict[str, Any]:
    """
    Get referral chain data for a Pandit.
    
    Task 10.16: Trust Data Selectors
    
    Returns:
        Dictionary with referral chain information
    
    Note:
        - Read-only data retrieval
        - NO computation
        - NO trust scoring
    """
    chain_data = {
        'has_referral': False,
        'referrer': None,
        'chain_length': 0,
    }
    
    # Check if Pandit has a referrer
    if hasattr(pandit, 'referred_by') and pandit.referred_by:
        referrer = pandit.referred_by
        chain_data['has_referral'] = True
        chain_data['referrer'] = {
            'id': referrer.id,
            'email': referrer.email,
            'full_name': referrer.get_full_name(),
        }
        
        # Calculate chain length (count how many levels up)
        chain_length = 1
        current = referrer
        while hasattr(current, 'referred_by') and current.referred_by:
            chain_length += 1
            current = current.referred_by
            # Prevent infinite loops
            if chain_length > 10:
                break
        
        chain_data['chain_length'] = chain_length
    
    return chain_data


def get_profile_completeness_for_pandit(pandit: User) -> Dict[str, Any]:
    """
    Get profile completeness data for a Pandit.
    
    Task 10.16: Trust Data Selectors
    
    Returns:
        Dictionary with profile completeness information
    
    Note:
        - Read-only data retrieval
        - NO computation
        - NO scoring
    """
    completeness_data = {
        'percentage': 0,
        'missing_fields': [],
        'is_complete': False,
    }
    
    try:
        profile = pandit.pandit_profile
    except PanditProfile.DoesNotExist:
        return completeness_data
    
    # Check required fields
    required_fields = [
        ('display_name', profile.display_name),
        ('about_description', profile.about_description),
        ('experience_years', profile.experience_years),
        ('languages_spoken', profile.languages_spoken),
        ('cities_served', profile.cities_served.exists()),
        ('areas_served', profile.areas_served.exists()),
        ('poojas_performed', profile.poojas_performed.exists()),
    ]
    
    completed_fields = sum(1 for _, value in required_fields if value)
    total_fields = len(required_fields)
    percentage = int((completed_fields / total_fields) * 100) if total_fields > 0 else 0
    
    missing_fields = [name for name, value in required_fields if not value]
    
    completeness_data['percentage'] = percentage
    completeness_data['missing_fields'] = missing_fields
    completeness_data['is_complete'] = percentage == 100
    
    return completeness_data


def get_rating_data_for_pandit(pandit: User) -> Dict[str, Any]:
    """
    Get rating data for a Pandit.
    
    Task 10.16: Trust Data Selectors
    
    Returns:
        Dictionary with rating aggregation data
    
    Note:
        - Uses ReviewService for aggregation
        - Read-only data retrieval
        - NO computation here (delegated to ReviewService)
    """
    try:
        # Use ReviewService to get rating aggregation
        rating_data = ReviewService.get_rating_aggregation_for_pandit(pandit.id)
        return rating_data
    except Exception:
        # Return default if error
        return {
            'average_rating': 0.0,
            'total_reviews': 0,
            'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }


def get_governance_state_for_pandit(pandit: User) -> Dict[str, Any]:
    """
    Get governance state for a Pandit.
    
    Task 10.16: Trust Data Selectors
    
    Returns:
        Dictionary with governance state information
    
    Note:
        - Read-only data retrieval
        - NO computation
        - NO governance decisions
    """
    governance_data = {
        'status': pandit.status if hasattr(pandit, 'status') else 'unknown',
        'is_active': pandit.is_active,
        'is_staff': pandit.is_staff,
        'is_superuser': pandit.is_superuser,
        'has_flagged_reviews': False,
        'has_flagged_intents': False,
    }
    
    # Check for flagged reviews
    try:
        from reviews.models import Review
        flagged_reviews_count = Review.objects.filter(
            pandit=pandit,
            is_reported=True
        ).count()
        governance_data['has_flagged_reviews'] = flagged_reviews_count > 0
        governance_data['flagged_reviews_count'] = flagged_reviews_count
    except Exception:
        pass
    
    # Check for flagged booking intents
    try:
        from booking_intent.models import BookingIntent
        flagged_intents_count = BookingIntent.objects.filter(
            pandit=pandit,
            is_flagged=True
        ).count()
        governance_data['has_flagged_intents'] = flagged_intents_count > 0
        governance_data['flagged_intents_count'] = flagged_intents_count
    except Exception:
        pass
    
    return governance_data
