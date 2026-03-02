"""
Serializers for search API.

Task 7.14: Search API (Read-Only)

Helper functions for serializing search request/response.
Read-only, no mutations.

Note: Using plain Python dicts instead of DRF serializers
to avoid dependency on Django REST Framework.
"""

from django.contrib.auth import get_user_model
from profiles.models import PanditProfile
from masterdata.models import City, LocalArea, Pooja

User = get_user_model()


class SearchRequestSerializer:
    """
    Helper class for search request validation.
    
    All fields are optional - search can be performed with any combination.
    """
    
    @staticmethod
    def validate(data):
        """Validate search parameters."""
        errors = {}
        
        if 'day_of_week' in data and 'specific_date' in data:
            if data['day_of_week'] is not None and data['specific_date'] is not None:
                errors['non_field_errors'] = ["Cannot specify both day_of_week and specific_date"]
        
        return errors


class PanditSearchResultSerializer:
    """
    Helper class for serializing Pandit search results.
    
    Includes user identity and profile data.
    Read-only, no mutations.
    """
    
    @staticmethod
    def serialize(pandit):
        """Serialize a single Pandit for search results."""
        result = {
            'id': pandit.id,
            'email': pandit.email,
            'full_name': pandit.get_full_name(),
            'created_at': pandit.created_at.isoformat() if pandit.created_at else None,
        }
        
        # Add profile data if exists
        if hasattr(pandit, 'pandit_profile'):
            profile = pandit.pandit_profile
            result['profile'] = {
                'display_name': profile.display_name,
                'about_description': profile.about_description,
                'experience_years': profile.experience_years,
                'languages_spoken': profile.languages_spoken,
                'cities_served': [
                    {'id': c.id, 'name': c.name, 'state': c.state}
                    for c in profile.cities_served.filter(is_active=True)
                ],
                'areas_served': [
                    {'id': a.id, 'name': a.name, 'city': {'id': a.city.id, 'name': a.city.name}}
                    for a in profile.areas_served.filter(is_active=True)
                ],
                'poojas_performed': [
                    {'id': p.id, 'name': p.name}
                    for p in profile.poojas_performed.filter(is_active=True)
                ],
            }
        
        return result

