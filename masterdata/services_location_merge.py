"""
Service functions for location rename and merge operations.

TASK 24: Location / Area Renamed or Merged

This module handles:
- Renaming locations (display_name only)
- Merging locations (one becomes primary, others inactive)
- Preserving historical references
"""

import logging
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import City, LocalArea

User = get_user_model()
logger = logging.getLogger(__name__)


def rename_city(city, new_name, actor=None):
    """
    TASK 24: Rename a city (display_name only, ID unchanged).
    
    Args:
        city: City instance
        new_name: New display name
        actor: User performing the rename
    
    Returns:
        Updated City instance
    """
    with transaction.atomic():
        old_name = city.name
        city.name = new_name
        city.save(update_fields=['name', 'updated_at'])
        
        # Log audit event
        try:
            from core.audit import log_deactivation
            log_deactivation(
                city,
                actor=actor,
                reason=f"LOCATION_RENAMED - City renamed from '{old_name}' to '{new_name}'"
            )
        except Exception:
            pass
        
        logger.info(f"TASK 24: City {city.id} renamed from '{old_name}' to '{new_name}'")
        
        return city


def rename_local_area(area, new_name, actor=None):
    """
    TASK 24: Rename a local area (display_name only, ID unchanged).
    
    Args:
        area: LocalArea instance
        new_name: New display name
        actor: User performing the rename
    
    Returns:
        Updated LocalArea instance
    """
    with transaction.atomic():
        old_name = area.name
        area.name = new_name
        area.save(update_fields=['name', 'updated_at'])
        
        # Log audit event
        try:
            from core.audit import log_deactivation
            log_deactivation(
                area,
                actor=actor,
                reason=f"LOCATION_RENAMED - Area renamed from '{old_name}' to '{new_name}'"
            )
        except Exception:
            pass
        
        logger.info(f"TASK 24: Local Area {area.id} renamed from '{old_name}' to '{new_name}'")
        
        return area


def merge_cities(primary_city, cities_to_merge, actor=None):
    """
    TASK 24: Merge multiple cities into one primary city.
    
    Args:
        primary_city: City instance that becomes the primary
        cities_to_merge: List of City instances to merge
        actor: User performing the merge
    
    Returns:
        dict: Summary of merge operation
    """
    with transaction.atomic():
        merged_count = 0
        
        for city in cities_to_merge:
            if city.id == primary_city.id:
                continue  # Skip primary city
            
            # Mark as inactive and set merged_into
            city.status = City.STATUS_INACTIVE
            city.is_active = False
            city.merged_into = primary_city
            city.save(update_fields=['status', 'is_active', 'merged_into', 'updated_at'])
            merged_count += 1
        
        # Log audit event
        try:
            from core.audit import log_deactivation
            log_deactivation(
                primary_city,
                actor=actor,
                reason=f"LOCATION_MERGED - {merged_count} city/cities merged into '{primary_city.name}'"
            )
        except Exception:
            pass
        
        logger.info(f"TASK 24: {merged_count} cities merged into primary city {primary_city.id} ({primary_city.name})")
        
        return {
            'primary_city': primary_city,
            'merged_count': merged_count
        }


def merge_local_areas(primary_area, areas_to_merge, actor=None):
    """
    TASK 24: Merge multiple local areas into one primary area.
    
    Args:
        primary_area: LocalArea instance that becomes the primary
        areas_to_merge: List of LocalArea instances to merge
        actor: User performing the merge
    
    Returns:
        dict: Summary of merge operation
    """
    with transaction.atomic():
        merged_count = 0
        
        for area in areas_to_merge:
            if area.id == primary_area.id:
                continue  # Skip primary area
            
            # Mark as inactive and set merged_into
            area.status = LocalArea.STATUS_INACTIVE
            area.is_active = False
            area.merged_into = primary_area
            area.save(update_fields=['status', 'is_active', 'merged_into', 'updated_at'])
            merged_count += 1
        
        # Log audit event
        try:
            from core.audit import log_deactivation
            log_deactivation(
                primary_area,
                actor=actor,
                reason=f"LOCATION_MERGED - {merged_count} area(s) merged into '{primary_area.name}'"
            )
        except Exception:
            pass
        
        logger.info(f"TASK 24: {merged_count} areas merged into primary area {primary_area.id} ({primary_area.name})")
        
        return {
            'primary_area': primary_area,
            'merged_count': merged_count
        }


def get_merged_location_display(location):
    """
    TASK 24: Get display text for merged location.
    
    Args:
        location: City or LocalArea instance
    
    Returns:
        str: Display text indicating merge status
    """
    if location.merged_into:
        if isinstance(location, City):
            return f"Now part of {location.merged_into.name}"
        else:
            return f"Now part of {location.merged_into.name}"
    return location.name







