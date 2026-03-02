"""
Follow Service Layer

Non-blocking service functions for follow/unfollow operations.
No logic mixed into views, no permission changes.
"""

from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from .models_follow import Follow
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


def follow_entity(user, entity_type, entity_id):
    """
    Follow an entity (pandit or temple).
    
    Args:
        user: User instance (must be End User - role='user')
        entity_type: 'pandit' or 'temple'
        entity_id: ID of the entity (PanditProfile.id or Page.id)
    
    Returns:
        tuple: (success: bool, follow_instance: Follow or None, message: str)
    
    Rules:
    - Silent fail if duplicate (returns success=False with message)
    - Only End Users can follow (role='user')
    - Validates entity exists before creating follow
    """
    if not user or not user.is_authenticated:
        return False, None, "User must be authenticated"
    
    # Only End Users can follow pandits; any authenticated user can follow temples
    if entity_type == 'pandit' and user.role != 'user':
        return False, None, "Only End Users can follow pandits"
    
    # Validate entity_type
    if entity_type not in ['pandit', 'temple']:
        return False, None, f"Invalid entity_type: {entity_type}"
    
    # Validate entity exists
    if entity_type == 'pandit':
        try:
            from profiles.models import PanditProfile
            entity = PanditProfile.objects.get(id=entity_id)
        except PanditProfile.DoesNotExist:
            return False, None, "Pandit not found"
    elif entity_type == 'temple':
        try:
            from pages.models import Page
            entity = Page.objects.get(id=entity_id)
        except Page.DoesNotExist:
            return False, None, "Temple not found"
    
    # Check if already following (silent check - don't fail loudly)
    if is_following(user, entity_type, entity_id):
        # Already following - return success but don't create duplicate
        logger.debug(f"User {user.email} already following {entity_type} #{entity_id}")
        return False, None, "Already following this entity"
    
    # Create follow relationship
    try:
        with transaction.atomic():
            follow = Follow.objects.create(
                user=user,
                entity_type=entity_type,
                entity_id=entity_id
            )
            logger.info(f"User {user.email} started following {entity_type} #{entity_id}")
            return True, follow, "Successfully followed"
    except IntegrityError:
        # Duplicate follow (race condition - another request created it)
        logger.warning(f"Duplicate follow attempt (race condition): {user.email} -> {entity_type} #{entity_id}")
        # Check again - might have been created by another request
        if is_following(user, entity_type, entity_id):
            return False, None, "Already following this entity"
        return False, None, "Failed to create follow relationship"
    except Exception as e:
        logger.error(f"Error creating follow: {str(e)}", exc_info=True)
        return False, None, f"Error following entity: {str(e)}"


def unfollow_entity(user, entity_type, entity_id):
    """
    Unfollow an entity.
    
    Args:
        user: User instance
        entity_type: 'pandit' or 'temple'
        entity_id: ID of the entity
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not user or not user.is_authenticated:
        return False, "User must be authenticated"
    
    try:
        follow = Follow.objects.get(
            user=user,
            entity_type=entity_type,
            entity_id=entity_id
        )
        follow.delete()  # Now allowed - users can unfollow
        logger.info(f"User {user.email} unfollowed {entity_type} #{entity_id}")
        return True, "Successfully unfollowed"
    except Follow.DoesNotExist:
        return False, "Not following this entity"
    except Exception as e:
        logger.error(f"Error unfollowing: {str(e)}", exc_info=True)
        return False, f"Error unfollowing entity: {str(e)}"


def is_following(user, entity_type, entity_id):
    """
    Check if user is following an entity.
    
    Args:
        user: User instance
        entity_type: 'pandit' or 'temple'
        entity_id: ID of the entity
    
    Returns:
        bool: True if following, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    return Follow.objects.filter(
        user=user,
        entity_type=entity_type,
        entity_id=entity_id
    ).exists()


def get_followers(entity_type, entity_id):
    """
    Get all followers of an entity.
    
    Args:
        entity_type: 'pandit' or 'temple'
        entity_id: ID of the entity
    
    Returns:
        QuerySet of User instances who follow this entity
    """
    follow_ids = Follow.objects.filter(
        entity_type=entity_type,
        entity_id=entity_id
    ).values_list('user_id', flat=True)
    
    return User.objects.filter(id__in=follow_ids)


def get_follower_count(entity_type, entity_id):
    """
    Get count of followers for an entity.
    
    Args:
        entity_type: 'pandit' or 'temple'
        entity_id: ID of the entity
    
    Returns:
        int: Number of followers
    """
    return Follow.objects.filter(
        entity_type=entity_type,
        entity_id=entity_id
    ).count()

