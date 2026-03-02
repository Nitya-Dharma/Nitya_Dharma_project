"""
Service functions for saved search operations.

TASK 20: Saved Searches with Removed Entities

This module ensures that saved searches are resilient to removed or inactive entities.
"""

import logging
from typing import Dict, Optional, Tuple
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import SavedSearch
from masterdata.models import City, LocalArea, Pooja

User = get_user_model()
logger = logging.getLogger(__name__)


def validate_and_clean_filters(filters: Dict) -> Tuple[Dict, list]:
    """
    TASK 20: Validate and clean search filters, removing invalid or inactive entities.
    
    Args:
        filters: Dictionary of search filters
    
    Returns:
        Tuple of (cleaned_filters, removed_filters_list)
    """
    cleaned_filters = filters.copy()
    removed_filters = []
    
    # Validate city_id
    if 'city_id' in cleaned_filters:
        city_id = cleaned_filters.get('city_id')
        if city_id:
            try:
                city = City.objects.get(id=city_id, is_active=True)
                # City is valid and active
            except City.DoesNotExist:
                removed_filters.append('city_id')
                del cleaned_filters['city_id']
                logger.info(f"TASK 20: Removed invalid city_id filter: {city_id}")
    
    # Validate area_id
    if 'area_id' in cleaned_filters:
        area_id = cleaned_filters.get('area_id')
        if area_id:
            try:
                area = LocalArea.objects.get(id=area_id, is_active=True)
                # If city_id is also present, validate area belongs to city
                if 'city_id' in cleaned_filters and cleaned_filters.get('city_id'):
                    if area.city_id != cleaned_filters['city_id']:
                        removed_filters.append('area_id')
                        del cleaned_filters['area_id']
                        logger.info(f"TASK 20: Removed area_id filter (doesn't belong to city): {area_id}")
            except LocalArea.DoesNotExist:
                removed_filters.append('area_id')
                del cleaned_filters['area_id']
                logger.info(f"TASK 20: Removed invalid area_id filter: {area_id}")
    
    # Validate pooja_id
    if 'pooja_id' in cleaned_filters:
        pooja_id = cleaned_filters.get('pooja_id')
        if pooja_id:
            try:
                pooja = Pooja.objects.get(id=pooja_id, is_active=True)
                # Pooja is valid and active
            except Pooja.DoesNotExist:
                removed_filters.append('pooja_id')
                del cleaned_filters['pooja_id']
                logger.info(f"TASK 20: Removed invalid pooja_id filter: {pooja_id}")
    
    # Validate page_type (if exists in constants)
    if 'page_type' in cleaned_filters:
        page_type = cleaned_filters.get('page_type')
        if page_type:
            try:
                from pages.constants import PAGE_TYPE_CHOICES
                valid_types = [choice[0] for choice in PAGE_TYPE_CHOICES]
                if page_type not in valid_types:
                    removed_filters.append('page_type')
                    del cleaned_filters['page_type']
                    logger.info(f"TASK 20: Removed invalid page_type filter: {page_type}")
            except ImportError:
                # If constants don't exist, keep the filter
                pass
    
    return cleaned_filters, removed_filters


def execute_saved_search(saved_search: SavedSearch) -> Tuple[Dict, list]:
    """
    TASK 20: Execute a saved search with filter validation.
    
    Args:
        saved_search: SavedSearch instance
    
    Returns:
        Tuple of (cleaned_filters, removed_filters_list)
    """
    # Validate and clean filters
    cleaned_filters, removed_filters = validate_and_clean_filters(saved_search.filters)
    
    # Update saved search with cleaned filters if any were removed
    if removed_filters:
        with transaction.atomic():
            saved_search.filters = cleaned_filters
            saved_search.save(update_fields=['filters', 'updated_at'])
            
            # Log audit event
            try:
                from core.audit import log_deactivation
                log_deactivation(
                    saved_search,
                    actor=None,
                    reason=f"SAVED_SEARCH_FILTER_REMOVED - Removed filters: {', '.join(removed_filters)}"
                )
            except Exception:
                pass
            
            logger.info(
                f"TASK 20: Saved search {saved_search.id} executed with removed filters: {removed_filters}"
            )
    
    # Update last_executed_at
    from django.utils import timezone
    saved_search.last_executed_at = timezone.now()
    saved_search.save(update_fields=['last_executed_at'])
    
    # Log audit event
    try:
        from core.audit import log_deactivation
        log_deactivation(
            saved_search,
            actor=None,
            reason="SAVED_SEARCH_EXECUTED_WITH_FALLBACK" if removed_filters else "SAVED_SEARCH_EXECUTED"
        )
    except Exception:
        pass
    
    return cleaned_filters, removed_filters


def get_user_message_for_removed_filters(removed_filters: list) -> Optional[str]:
    """
    TASK 20: Get user-friendly message for removed filters.
    
    Args:
        removed_filters: List of removed filter keys
    
    Returns:
        User message or None if no filters removed
    """
    if not removed_filters:
        return None
    
    return "Some filters are no longer available and were removed."







