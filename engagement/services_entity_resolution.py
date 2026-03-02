"""
Service functions for resolving entities in engagement events.

TASK 26: Engagement Events Tied to Removed Entities

This module ensures that:
- Engagement events can resolve entities even if they're INVISIBLE
- Entity public_id remains resolvable forever
- No FK breaks occur
"""

import logging
from typing import Optional, Dict, Any
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


def resolve_entity_by_public_id(entity_type: str, entity_public_id: str) -> Optional[Dict[str, Any]]:
    """
    TASK 26: Resolve entity by public_id regardless of status (ACTIVE/INVISIBLE).
    
    This function allows engagement events to resolve entities even if they're
    marked as INVISIBLE or DEACTIVATED. The entity row must exist, but status
    doesn't matter for engagement event queries.
    
    Args:
        entity_type: Type of entity (e.g., 'TEMPLE_PAGE', 'PAGE_POST')
        entity_public_id: Public ID (UUIDv7) of the entity
    
    Returns:
        dict: Entity information including status, or None if not found
    """
    try:
        if entity_type == 'TEMPLE_PAGE' or entity_type == 'PAGE':
            from pages.models import Page
            try:
                entity = Page.objects.get(public_id=entity_public_id)
                return {
                    'id': entity.id,
                    'public_id': entity.public_id,
                    'title': entity.title,
                    'status': entity.status,
                    'is_visible': entity.status == 'ACTIVE',
                    'entity_type': entity_type
                }
            except Page.DoesNotExist:
                logger.warning(f"TASK 26: Entity not found - type: {entity_type}, public_id: {entity_public_id}")
                return None
        
        elif entity_type == 'PAGE_POST':
            from pages.models import PagePost
            try:
                entity = PagePost.objects.get(public_id=entity_public_id)
                return {
                    'id': entity.id,
                    'public_id': entity.public_id,
                    'title': entity.title,
                    'status': entity.status,
                    'is_visible': entity.status == 'VISIBLE',
                    'entity_type': entity_type
                }
            except PagePost.DoesNotExist:
                logger.warning(f"TASK 26: Entity not found - type: {entity_type}, public_id: {entity_public_id}")
                return None
        
        else:
            logger.warning(f"TASK 26: Unknown entity type: {entity_type}")
            return None
    
    except Exception as e:
        logger.error(f"TASK 26: Error resolving entity - type: {entity_type}, public_id: {entity_public_id}, error: {str(e)}")
        return None


def get_engagement_events_for_entity(entity_type: str, entity_public_id: str, include_invisible: bool = True):
    """
    TASK 26: Get engagement events for an entity, including invisible entities.
    
    Args:
        entity_type: Type of entity
        entity_public_id: Public ID of the entity
        include_invisible: If True, include events even if entity is INVISIBLE
    
    Returns:
        QuerySet of UserInteractionEvent instances
    """
    from .models import UserInteractionEvent
    
    queryset = UserInteractionEvent.objects.filter(
        entity_type=entity_type,
        entity_public_id=entity_public_id
    )
    
    # TASK 26: Always return events regardless of entity status
    # The entity may be INVISIBLE, but engagement history is preserved
    return queryset.order_by('-created_at')


def get_entity_display_for_engagement(entity_type: str, entity_public_id: str) -> str:
    """
    TASK 26: Get display text for entity in engagement context.
    
    If entity is invisible, shows appropriate message.
    
    Args:
        entity_type: Type of entity
        entity_public_id: Public ID of the entity
    
    Returns:
        str: Display text
    """
    entity_info = resolve_entity_by_public_id(entity_type, entity_public_id)
    
    if not entity_info:
        return "This content is no longer available"
    
    if not entity_info.get('is_visible', False):
        return "This content is no longer available"
    
    return entity_info.get('title', 'Unknown Entity')







