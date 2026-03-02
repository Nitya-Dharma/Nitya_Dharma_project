"""
Booking Intent Serializers

Task 8.14: Booking Intent API Serialization

Serializes BookingIntent models to JSON for API responses.
Read-only serialization, no mutations.
"""

from typing import List, Dict, Any
from .models import BookingIntent


class BookingIntentSerializer:
    """
    Serializer for BookingIntent models.
    
    All methods are static and read-only.
    No mutations, no side effects.
    """
    
    @staticmethod
    def serialize(intent: BookingIntent) -> Dict[str, Any]:
        """
        Serialize a single BookingIntent to dictionary.
        
        Security: Returns public_id instead of internal id.
        
        Args:
            intent: BookingIntent instance
        
        Returns:
            Dictionary representation of the intent
        """
        return {
            'public_id': intent.public_id,  # Use public_id for URLs/APIs
            'requester': {
                'public_id': intent.requester.public_id,  # Use public_id
                'email': intent.requester.email,
                'full_name': intent.requester.get_full_name(),
            },
            'pandit': {
                'public_id': intent.pandit.public_id,  # Use public_id
                'email': intent.pandit.email,
                'full_name': intent.pandit.get_full_name(),
            },
            'optional_requested_date': intent.optional_requested_date.isoformat() if intent.optional_requested_date else None,
            'optional_requested_time': intent.optional_requested_time.isoformat() if intent.optional_requested_time else None,
            'message': intent.message,
            'status': intent.status,
            'status_display': intent.get_status_display() if hasattr(intent, 'get_status_display') else intent.status,
            'created_at': intent.created_at.isoformat() if intent.created_at else None,
            'updated_at': intent.updated_at.isoformat() if intent.updated_at else None,
            'is_flagged': intent.is_flagged,
            'flagged_at': intent.flagged_at.isoformat() if intent.flagged_at else None,
            'flagged_reason': intent.flagged_reason,
        }
    
    @staticmethod
    def serialize_list(intents) -> List[Dict[str, Any]]:
        """
        Serialize a list/queryset of BookingIntents to list of dictionaries.
        
        Args:
            intents: List or QuerySet of BookingIntent instances
        
        Returns:
            List of dictionary representations
        """
        return [BookingIntentSerializer.serialize(intent) for intent in intents]
