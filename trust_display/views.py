"""
Trust display API views.

Task 10.17: Trust Data Exposure APIs

Backend-only, read-only APIs for trust display.
NO computation, NO mutation, NO business logic.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from .selectors import (
    get_referral_chain_for_pandit,
    get_profile_completeness_for_pandit,
    get_rating_data_for_pandit,
    get_governance_state_for_pandit
)
from .serializers import TrustDisplaySerializer

User = get_user_model()
logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def get_trust_display(request, pandit_id):
    """
    Get trust display data for a Pandit.
    
    Task 10.17: Trust Data Exposure APIs
    
    GET /api/trust-display/pandit/<pandit_id>/
    
    Returns:
        JSON response with trust display data
    
    Note:
        - Read-only aggregation
        - NO computation
        - NO mutation
        - NO caching of governance state
    """
    try:
        pandit = User.objects.get(id=pandit_id, role='pandit', is_active=True)
    except User.DoesNotExist:
        return JsonResponse(
            {'error': 'Pandit not found'},
            status=404
        )
    
    # Read-only data aggregation (NO computation)
    referral_chain = get_referral_chain_for_pandit(pandit)
    profile_completeness = get_profile_completeness_for_pandit(pandit)
    rating_data = get_rating_data_for_pandit(pandit)
    governance_state = get_governance_state_for_pandit(pandit)
    
    # Check if user is admin (for sensitive data)
    include_sensitive = request.user.is_authenticated and request.user.role == 'admin'
    
    # Serialize trust display data
    trust_data = TrustDisplaySerializer.serialize_trust_data(
        pandit=pandit,
        referral_chain=referral_chain,
        profile_completeness=profile_completeness,
        rating_data=rating_data,
        governance_state=governance_state,
        include_sensitive=include_sensitive
    )
    
    return JsonResponse(trust_data)


@require_http_methods(["GET"])
def get_trust_badges(request, pandit_id):
    """
    Get trust badges only for a Pandit.
    
    Task 10.17: Trust Data Exposure APIs
    
    GET /api/trust-display/pandit/<pandit_id>/badges/
    
    Returns:
        JSON response with trust badges (labels only)
    
    Note:
        - Badges are labels only
        - No scoring
        - No ranking
    """
    try:
        pandit = User.objects.get(id=pandit_id, role='pandit', is_active=True)
    except User.DoesNotExist:
        return JsonResponse(
            {'error': 'Pandit not found'},
            status=404
        )
    
    # Read-only data aggregation
    referral_chain = get_referral_chain_for_pandit(pandit)
    profile_completeness = get_profile_completeness_for_pandit(pandit)
    rating_data = get_rating_data_for_pandit(pandit)
    governance_state = get_governance_state_for_pandit(pandit)
    
    # Generate badges only
    badges = TrustDisplaySerializer._generate_trust_badges(
        referral_chain,
        profile_completeness,
        rating_data,
        governance_state
    )
    
    return JsonResponse({
        'pandit_id': pandit.id,
        'badges': badges
    })
