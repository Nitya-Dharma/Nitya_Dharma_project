"""
Review Serializers

Task 9.14: Review API Serialization

Serializes Review models to JSON for API responses.
Read-only serialization, no mutations.
"""

from typing import List, Dict, Any, Optional
from .models import Review


class ReviewSerializer:
    """
    Serializer for Review models.
    
    All methods are static and read-only.
    No mutations, no side effects.
    """
    
    @staticmethod
    def serialize(review: Review, include_metadata: bool = False) -> Dict[str, Any]:
        """
        Serialize a single Review to dictionary.
        
        Args:
            review: Review instance
            include_metadata: Whether to include additional metadata (admin-only fields)
        
        Returns:
            Dictionary representation of the review
        """
        result = {
            'public_id': review.public_id,  # Use public_id for URLs/APIs
            'user': {
                'public_id': review.user.public_id,  # Use public_id
                'email': review.user.email,
                'full_name': review.user.get_full_name(),
            },
            'pandit': {
                'public_id': review.pandit.public_id,  # Use public_id
                'email': review.pandit.email,
                'full_name': review.pandit.get_full_name(),
            },
            'rating': review.rating,
            'review_text': review.review_text,
            'visibility_state': review.visibility_state,
            'visibility_state_display': review.get_visibility_state_display() if hasattr(review, 'get_visibility_state_display') else review.visibility_state,
            'is_reported': review.is_reported,
            'created_at': review.created_at.isoformat() if review.created_at else None,
            'updated_at': review.updated_at.isoformat() if review.updated_at else None,
        }
        
        # Include metadata if requested (admin-only fields)
        if include_metadata:
            result['metadata'] = {
                'created_source': review.created_source,
                'created_source_display': review.get_created_source_display() if hasattr(review, 'get_created_source_display') else review.created_source,
                'reported_at': review.reported_at.isoformat() if review.reported_at else None,
                'reported_reason': review.reported_reason,
                'last_visibility_change_at': review.last_visibility_change_at.isoformat() if review.last_visibility_change_at else None,
                'reviewer_status_at_creation': review.reviewer_status_at_creation,
                'pandit_status_at_creation': review.pandit_status_at_creation,
            }
        
        return result
    
    @staticmethod
    def serialize_list(reviews, include_metadata: bool = False) -> List[Dict[str, Any]]:
        """
        Serialize a list/queryset of Reviews to list of dictionaries.
        
        Args:
            reviews: List or QuerySet of Review instances
            include_metadata: Whether to include additional metadata
        
        Returns:
            List of dictionary representations
        """
        return [ReviewSerializer.serialize(review, include_metadata) for review in reviews]
