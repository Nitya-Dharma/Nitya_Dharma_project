"""
Engagement services for recording user behavior events.

STRICT RULES:
- NO analytics computation
- NO ranking or scoring
- NO sentiment analysis
- NO aggregation beyond simple counts
- RAW FACTS ONLY

All functions validate inputs, enforce rate limits (basic), and insert rows safely.
Future: Feed engine will consume these events.
"""

import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import UserInteractionEvent, PostComment, PostLike
from .constants import (
    INTERACTION_VIEW,
    INTERACTION_CLICK,
    INTERACTION_LIKE,
    INTERACTION_UNLIKE,
    INTERACTION_SHARE,
    INTERACTION_COMMENT_CREATE,
    INTERACTION_COMMENT_DELETE,
    INTERACTION_PIN,
    INTERACTION_UNPIN,
    ENTITY_TYPES,
    INTERACTION_TYPES,
    COMMENT_STATUS_ACTIVE,
)

logger = logging.getLogger(__name__)

# Basic rate limiting thresholds (events per minute)
RATE_LIMITS = {
    INTERACTION_VIEW: 100,  # Higher limit for views
    INTERACTION_CLICK: 50,
    INTERACTION_LIKE: 30,
    INTERACTION_UNLIKE: 30,
    INTERACTION_SHARE: 20,
    INTERACTION_COMMENT_CREATE: 10,
    INTERACTION_COMMENT_DELETE: 10,
    INTERACTION_PIN: 10,
    INTERACTION_UNPIN: 10,
}


def _check_rate_limit(user, interaction_type, entity_public_id=None):
    """
    Basic rate limiting check.
    
    Prevents spam by limiting events per minute per user.
    
    Args:
        user: User instance
        interaction_type: Type of interaction
        entity_public_id: Optional entity public ID (for per-entity limits)
    
    Returns:
        True if within limit, False if rate limited
    
    Note: This is basic protection. Advanced rate limiting handled at infrastructure level.
    """
    if interaction_type not in RATE_LIMITS:
        return True  # No limit defined, allow
    
    limit = RATE_LIMITS[interaction_type]
    since = timezone.now() - timedelta(minutes=1)
    
    # Count recent events of this type by this user
    recent_count = UserInteractionEvent.objects.filter(
        user=user,
        interaction_type=interaction_type,
        created_at__gte=since
    ).count()
    
    if recent_count >= limit:
        logger.warning(f"Rate limit exceeded for user {user.id}: {interaction_type} ({recent_count}/{limit})")
        return False
    
    return True


def _validate_metadata(metadata):
    """
    Validate metadata doesn't contain PII.
    
    Args:
        metadata: Dictionary to validate
    
    Returns:
        Validated metadata
    
    Raises:
        ValidationError: If PII is detected
    """
    if not metadata:
        return None
    
    if not isinstance(metadata, dict):
        raise ValidationError("Metadata must be a dictionary")
    
    forbidden_keys = ['email', 'phone', 'phone_number', 'whatsapp_number', 'ip_address', 'ip']
    for key in forbidden_keys:
        if key in metadata:
            raise ValidationError(f"Metadata cannot contain PII field: {key}")
    
    # Limit metadata size (prevent abuse)
    import json
    if len(json.dumps(metadata)) > 1000:
        raise ValidationError("Metadata size exceeds 1000 characters")
    
    return metadata


def record_view(user, entity_type, entity_public_id, metadata=None):
    """
    Record a VIEW interaction event.
    
    Args:
        user: User instance (must be authenticated)
        entity_type: Type of entity (from ENTITY_TYPES)
        entity_public_id: Public ID (UUIDv7) of the entity
        metadata: Optional metadata dictionary (no PII)
    
    Returns:
        UserInteractionEvent instance
    
    Raises:
        ValidationError: If inputs are invalid
    """
    if not user or not user.is_authenticated:
        raise ValidationError("User must be authenticated")
    
    if entity_type not in ENTITY_TYPES:
        raise ValidationError(f"Invalid entity_type: {entity_type}")
    
    if not entity_public_id:
        raise ValidationError("entity_public_id is required")
    
    # Basic rate limiting
    if not _check_rate_limit(user, INTERACTION_VIEW, entity_public_id):
        raise ValidationError("Rate limit exceeded for VIEW events")
    
    metadata = _validate_metadata(metadata)
    
    try:
        with transaction.atomic():
            event = UserInteractionEvent.objects.create(
                user=user,
                entity_type=entity_type,
                entity_public_id=entity_public_id,
                interaction_type=INTERACTION_VIEW,
                metadata=metadata
            )
            logger.debug(f"Recorded VIEW event: user={user.id}, entity={entity_type}:{entity_public_id[:8]}")
            return event
    except Exception as e:
        logger.error(f"Error recording VIEW event: {str(e)}", exc_info=True)
        raise


def record_click(user, entity_type, entity_public_id, metadata=None):
    """
    Record a CLICK interaction event.
    
    Args:
        user: User instance
        entity_type: Type of entity
        entity_public_id: Public ID of the entity
        metadata: Optional metadata
    
    Returns:
        UserInteractionEvent instance
    """
    if not user or not user.is_authenticated:
        raise ValidationError("User must be authenticated")
    
    if entity_type not in ENTITY_TYPES:
        raise ValidationError(f"Invalid entity_type: {entity_type}")
    
    if not entity_public_id:
        raise ValidationError("entity_public_id is required")
    
    if not _check_rate_limit(user, INTERACTION_CLICK, entity_public_id):
        raise ValidationError("Rate limit exceeded for CLICK events")
    
    metadata = _validate_metadata(metadata)
    
    try:
        with transaction.atomic():
            event = UserInteractionEvent.objects.create(
                user=user,
                entity_type=entity_type,
                entity_public_id=entity_public_id,
                interaction_type=INTERACTION_CLICK,
                metadata=metadata
            )
            logger.debug(f"Recorded CLICK event: user={user.id}, entity={entity_type}:{entity_public_id[:8]}")
            return event
    except Exception as e:
        logger.error(f"Error recording CLICK event: {str(e)}", exc_info=True)
        raise


def record_like(user, entity_type, entity_public_id):
    """
    Record a LIKE interaction event.
    
    Also creates/updates PostLike if entity_type is PAGE_POST.
    
    Args:
        user: User instance
        entity_type: Type of entity
        entity_public_id: Public ID of the entity
    
    Returns:
        Tuple (UserInteractionEvent, PostLike or None)
    """
    if not user or not user.is_authenticated:
        raise ValidationError("User must be authenticated")
    
    if entity_type not in ENTITY_TYPES:
        raise ValidationError(f"Invalid entity_type: {entity_type}")
    
    if not entity_public_id:
        raise ValidationError("entity_public_id is required")
    
    if not _check_rate_limit(user, INTERACTION_LIKE, entity_public_id):
        raise ValidationError("Rate limit exceeded for LIKE events")
    
    try:
        with transaction.atomic():
            # Record event
            event = UserInteractionEvent.objects.create(
                user=user,
                entity_type=entity_type,
                entity_public_id=entity_public_id,
                interaction_type=INTERACTION_LIKE,
                metadata=None
            )
            
            # If it's a post, also create PostLike for fast counting
            post_like = None
            if entity_type == 'PAGE_POST':
                post_like, created = PostLike.objects.get_or_create(
                    post_public_id=entity_public_id,
                    user=user
                )
                if not created:
                    # Already liked (shouldn't happen, but handle gracefully)
                    logger.warning(f"User {user.id} already liked post {entity_public_id[:8]}")
            
            logger.debug(f"Recorded LIKE event: user={user.id}, entity={entity_type}:{entity_public_id[:8]}")
            return event, post_like
    except Exception as e:
        logger.error(f"Error recording LIKE event: {str(e)}", exc_info=True)
        raise


def record_unlike(user, entity_type, entity_public_id):
    """
    Record an UNLIKE interaction event.
    
    Also removes PostLike if entity_type is PAGE_POST.
    
    Args:
        user: User instance
        entity_type: Type of entity
        entity_public_id: Public ID of the entity
    
    Returns:
        UserInteractionEvent instance
    """
    if not user or not user.is_authenticated:
        raise ValidationError("User must be authenticated")
    
    if entity_type not in ENTITY_TYPES:
        raise ValidationError(f"Invalid entity_type: {entity_type}")
    
    if not entity_public_id:
        raise ValidationError("entity_public_id is required")
    
    if not _check_rate_limit(user, INTERACTION_UNLIKE, entity_public_id):
        raise ValidationError("Rate limit exceeded for UNLIKE events")
    
    try:
        with transaction.atomic():
            # Record event
            event = UserInteractionEvent.objects.create(
                user=user,
                entity_type=entity_type,
                entity_public_id=entity_public_id,
                interaction_type=INTERACTION_UNLIKE,
                metadata=None
            )
            
            # If it's a post, remove PostLike
            if entity_type == 'PAGE_POST':
                PostLike.objects.filter(
                    post_public_id=entity_public_id,
                    user=user
                ).delete()
            
            logger.debug(f"Recorded UNLIKE event: user={user.id}, entity={entity_type}:{entity_public_id[:8]}")
            return event
    except Exception as e:
        logger.error(f"Error recording UNLIKE event: {str(e)}", exc_info=True)
        raise


def record_share(user, entity_type, entity_public_id, metadata=None):
    """
    Record a SHARE interaction event.
    
    Args:
        user: User instance
        entity_type: Type of entity
        entity_public_id: Public ID of the entity
        metadata: Optional metadata (e.g., share_method: 'whatsapp', 'facebook')
    
    Returns:
        UserInteractionEvent instance
    """
    if not user or not user.is_authenticated:
        raise ValidationError("User must be authenticated")
    
    if entity_type not in ENTITY_TYPES:
        raise ValidationError(f"Invalid entity_type: {entity_type}")
    
    if not entity_public_id:
        raise ValidationError("entity_public_id is required")
    
    if not _check_rate_limit(user, INTERACTION_SHARE, entity_public_id):
        raise ValidationError("Rate limit exceeded for SHARE events")
    
    metadata = _validate_metadata(metadata)
    
    try:
        with transaction.atomic():
            event = UserInteractionEvent.objects.create(
                user=user,
                entity_type=entity_type,
                entity_public_id=entity_public_id,
                interaction_type=INTERACTION_SHARE,
                metadata=metadata
            )
            logger.debug(f"Recorded SHARE event: user={user.id}, entity={entity_type}:{entity_public_id[:8]}")
            return event
    except Exception as e:
        logger.error(f"Error recording SHARE event: {str(e)}", exc_info=True)
        raise


def create_comment(user, post_public_id, comment_text, parent_comment_public_id=None):
    """
    Create a comment on a post.
    
    Also records a COMMENT_CREATE interaction event.
    
    Args:
        user: User instance
        post_public_id: Public ID (UUIDv7) of the post
        comment_text: Comment content (max 2000 chars)
        parent_comment_public_id: Optional parent comment public ID (for replies)
    
    Returns:
        PostComment instance
    """
    if not user or not user.is_authenticated:
        raise ValidationError("User must be authenticated")
    
    if not post_public_id:
        raise ValidationError("post_public_id is required")
    
    if not comment_text or not comment_text.strip():
        raise ValidationError("comment_text is required")
    
    if len(comment_text) > 2000:
        raise ValidationError("comment_text must be 2000 characters or less")
    
    if not _check_rate_limit(user, INTERACTION_COMMENT_CREATE):
        raise ValidationError("Rate limit exceeded for COMMENT_CREATE events")
    
    try:
        with transaction.atomic():
            # Get parent comment if specified
            parent_comment = None
            if parent_comment_public_id:
                try:
                    parent_comment = PostComment.objects.get(public_id=parent_comment_public_id)
                except PostComment.DoesNotExist:
                    raise ValidationError(f"Parent comment not found: {parent_comment_public_id}")
            
            # Create comment
            comment = PostComment.objects.create(
                post_public_id=post_public_id,
                user=user,
                parent_comment=parent_comment,
                comment_text=comment_text.strip(),
                status=COMMENT_STATUS_ACTIVE
            )
            
            # Record event
            UserInteractionEvent.objects.create(
                user=user,
                entity_type='PAGE_POST',
                entity_public_id=post_public_id,
                interaction_type=INTERACTION_COMMENT_CREATE,
                metadata={'comment_public_id': comment.public_id}
            )
            
            logger.debug(f"Created comment: user={user.id}, post={post_public_id[:8]}, comment={comment.public_id[:8]}")
            return comment
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}", exc_info=True)
        raise


def delete_comment(user, comment_public_id):
    """
    Delete a comment (soft delete - sets status to hidden).
    
    Also records a COMMENT_DELETE interaction event.
    
    Args:
        user: User instance (must be comment owner or admin)
        comment_public_id: Public ID (UUIDv7) of the comment
    
    Returns:
        PostComment instance (with status='hidden')
    
    Note: Hard delete not allowed. Governance module handles permanent removal.
    """
    if not user or not user.is_authenticated:
        raise ValidationError("User must be authenticated")
    
    if not comment_public_id:
        raise ValidationError("comment_public_id is required")
    
    try:
        comment = PostComment.objects.get(public_id=comment_public_id)
    except PostComment.DoesNotExist:
        raise ValidationError(f"Comment not found: {comment_public_id}")
    
    # Check ownership or admin
    if comment.user != user and not (user.is_staff or user.is_superuser):
        raise ValidationError("You do not have permission to delete this comment")
    
    if not _check_rate_limit(user, INTERACTION_COMMENT_DELETE):
        raise ValidationError("Rate limit exceeded for COMMENT_DELETE events")
    
    try:
        with transaction.atomic():
            # Soft delete (set status to hidden)
            comment.status = 'hidden'
            comment.save(update_fields=['status'])
            
            # Record event
            UserInteractionEvent.objects.create(
                user=user,
                entity_type='PAGE_POST',
                entity_public_id=comment.post_public_id,
                interaction_type=INTERACTION_COMMENT_DELETE,
                metadata={'comment_public_id': comment.public_id}
            )
            
            logger.debug(f"Deleted comment: user={user.id}, comment={comment.public_id[:8]}")
            return comment
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}", exc_info=True)
        raise

