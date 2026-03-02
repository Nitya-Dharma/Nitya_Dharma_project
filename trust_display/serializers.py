"""
Trust Display Serializers

Task 10.17: Trust Data Exposure APIs

Serializes trust display data to JSON for API responses.
Read-only serialization, no mutations.
"""

from typing import Dict, Any, List, Optional
from django.contrib.auth import get_user_model

User = get_user_model()


class TrustDisplaySerializer:
    """
    Serializer for trust display data.
    
    All methods are static and read-only.
    No mutations, no side effects.
    """
    
    @staticmethod
    def serialize_trust_data(
        pandit: User,
        referral_chain: Dict[str, Any],
        profile_completeness: Dict[str, Any],
        rating_data: Dict[str, Any],
        governance_state: Dict[str, Any],
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        Serialize complete trust display data.
        
        Args:
            pandit: Pandit User instance
            referral_chain: Referral chain data from selector
            profile_completeness: Profile completeness data from selector
            rating_data: Rating aggregation data from selector
            governance_state: Governance state data from selector
            include_sensitive: Whether to include sensitive/admin-only data
        
        Returns:
            Dictionary representation of trust display data
        """
        result = {
            'pandit': {
                'id': pandit.id,
                'email': pandit.email,
                'full_name': pandit.get_full_name(),
            },
            'referral_chain': referral_chain,
            'profile_completeness': profile_completeness,
            'rating_data': rating_data,
            'trust_badges': TrustDisplaySerializer._generate_trust_badges(
                referral_chain,
                profile_completeness,
                rating_data,
                governance_state
            ),
        }
        
        # Include sensitive data only if requested (admin-only)
        if include_sensitive:
            result['governance_state'] = governance_state
        
        return result
    
    @staticmethod
    def _generate_trust_badges(
        referral_chain: Dict[str, Any],
        profile_completeness: Dict[str, Any],
        rating_data: Dict[str, Any],
        governance_state: Dict[str, Any]
    ) -> List[str]:
        """
        Generate trust badges (labels only).
        
        Task 10.4: Trust Badge Display
        
        Args:
            referral_chain: Referral chain data
            profile_completeness: Profile completeness data
            rating_data: Rating aggregation data
            governance_state: Governance state data
        
        Returns:
            List of badge labels (strings only)
        
        Note:
            - Badges are labels only
            - No scoring
            - No ranking
            - Informational only
        """
        badges = []
        
        # Referral-based badges
        if referral_chain.get('has_referral'):
            badges.append('Referred Pandit')
            if referral_chain.get('chain_length', 0) > 1:
                badges.append('Multi-Level Referral')
        
        # Profile completeness badges
        if profile_completeness.get('is_complete'):
            badges.append('Complete Profile')
        elif profile_completeness.get('percentage', 0) >= 80:
            badges.append('Mostly Complete Profile')
        
        # Rating-based badges
        avg_rating = rating_data.get('average_rating', 0.0)
        total_reviews = rating_data.get('total_reviews', 0)
        
        if total_reviews >= 10:
            badges.append('Experienced')
        if avg_rating >= 4.5 and total_reviews >= 5:
            badges.append('Highly Rated')
        elif avg_rating >= 4.0 and total_reviews >= 3:
            badges.append('Well Rated')
        
        # Governance badges (neutral, informational only)
        if governance_state.get('status') == 'active':
            badges.append('Active Pandit')
        
        # No negative badges (trust display is neutral)
        # Governance issues are handled separately, not shown as badges
        
        return badges
