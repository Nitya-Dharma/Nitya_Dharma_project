"""
Master Data Service Functions

Provides read-only access to active master data for use in filters, dropdowns, and forms.
All functions return only ACTIVE records, sorted alphabetically.
"""

from typing import List, Optional
from .models import City, Mandal, LocalArea, PoojaCategory, Pooja


def get_active_cities() -> List[City]:
    """
    Get all active cities, sorted alphabetically.
    
    Returns:
        QuerySet of active City objects
    """
    return City.objects.filter(
        status=City.STATUS_ACTIVE,
        is_active=True
    ).order_by('name')


def get_active_mandals(city_id: Optional[int] = None) -> List[Mandal]:
    """
    Get all active mandals, optionally filtered by city.
    
    Args:
        city_id: Optional city ID to filter by
        
    Returns:
        QuerySet of active Mandal objects
    """
    queryset = Mandal.objects.filter(
        status=Mandal.STATUS_ACTIVE,
        is_active=True
    )
    
    if city_id:
        queryset = queryset.filter(city_id=city_id)
    
    return queryset.order_by('city__name', 'name')


def get_active_local_areas(mandal_id: Optional[int] = None, city_id: Optional[int] = None) -> List[LocalArea]:
    """
    Get all active local areas, optionally filtered by mandal or city.
    
    Args:
        mandal_id: Optional mandal ID to filter by
        city_id: Optional city ID to filter by
        
    Returns:
        QuerySet of active LocalArea objects
    """
    queryset = LocalArea.objects.filter(
        status=LocalArea.STATUS_ACTIVE,
        is_active=True
    )
    
    if mandal_id:
        queryset = queryset.filter(mandal_id=mandal_id)
    elif city_id:
        queryset = queryset.filter(city_id=city_id)
    
    return queryset.order_by('city__name', 'name')


def get_active_pooja_categories() -> List[PoojaCategory]:
    """
    Get all active pooja categories, sorted alphabetically.
    
    Returns:
        QuerySet of active PoojaCategory objects
    """
    return PoojaCategory.objects.filter(
        status=PoojaCategory.STATUS_ACTIVE
    ).order_by('name')


def get_active_poojas(category_id: Optional[int] = None) -> List[Pooja]:
    """
    Get all active poojas, optionally filtered by category.
    
    Args:
        category_id: Optional PoojaCategory ID to filter by
        
    Returns:
        QuerySet of active Pooja objects
    """
    queryset = Pooja.objects.filter(
        status=Pooja.STATUS_ACTIVE,
        is_active=True
    )
    
    if category_id:
        queryset = queryset.filter(pooja_category_id=category_id)
    
    return queryset.order_by('pooja_category__name', 'category', 'name')






