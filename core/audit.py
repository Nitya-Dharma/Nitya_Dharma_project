"""
Audit logging service for tracking deletion attempts and deactivation events.

This module provides centralized audit logging for:
- Blocked deletion attempts
- Deactivation events
- Reactivation events
- Custodianship assignments
"""

import logging
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


def log_blocked_deletion(entity, actor=None, reason=None):
    """
    Log a blocked deletion attempt.
    
    Args:
        entity: Model instance that was attempted to be deleted
        actor (User, optional): User who attempted the deletion
        reason (str, optional): Reason for blocking
    
    Returns:
        None
    """
    model_name = entity.__class__.__name__
    entity_id = getattr(entity, 'pk', 'unknown')
    actor_email = actor.email if actor else 'system'
    
    log_message = (
        f"DELETE_ATTEMPT_BLOCKED | "
        f"entity={model_name} | "
        f"entity_id={entity_id} | "
        f"actor={actor_email} | "
        f"reason={reason or 'Hard deletion not allowed'} | "
        f"timestamp={timezone.now().isoformat()}"
    )
    
    logger.warning(log_message)
    
    # TODO: Store in database audit table if needed
    # For now, using logging as the audit trail


def log_deactivation(entity, actor=None, reason=None):
    """
    Log a deactivation event.
    
    Args:
        entity: Model instance that was deactivated
        actor (User, optional): User who performed the deactivation
        reason (str, optional): Reason for deactivation
    
    Returns:
        None
    """
    model_name = entity.__class__.__name__
    entity_id = getattr(entity, 'pk', 'unknown')
    actor_email = actor.email if actor else 'system'
    
    log_message = (
        f"PANDIT_DEACTIVATED | "
        f"entity={model_name} | "
        f"entity_id={entity_id} | "
        f"actor={actor_email} | "
        f"reason={reason or 'Not provided'} | "
        f"timestamp={timezone.now().isoformat()}"
    )
    
    logger.info(log_message)
    
    # TODO: Store in database audit table if needed


def log_reactivation(entity, actor=None, reason=None):
    """
    Log a reactivation event.
    
    Args:
        entity: Model instance that was reactivated
        actor (User, optional): User who performed the reactivation
        reason (str, optional): Reason for reactivation
    
    Returns:
        None
    """
    model_name = entity.__class__.__name__
    entity_id = getattr(entity, 'pk', 'unknown')
    actor_email = actor.email if actor else 'system'
    
    log_message = (
        f"ENTITY_REACTIVATED | "
        f"entity={model_name} | "
        f"entity_id={entity_id} | "
        f"actor={actor_email} | "
        f"reason={reason or 'Not provided'} | "
        f"timestamp={timezone.now().isoformat()}"
    )
    
    logger.info(log_message)


def log_custodianship_assignment(original_referrer, custodian, reason=None, actor=None):
    """
    Log a referral custodianship assignment.
    
    Args:
        original_referrer: User instance (deactivated Pandit)
        custodian: User instance (Super Admin)
        reason (str, optional): Reason for assignment
        actor (User, optional): User who performed the assignment
    
    Returns:
        None
    """
    referrer_id = getattr(original_referrer, 'pk', 'unknown')
    referrer_email = getattr(original_referrer, 'email', 'unknown')
    custodian_email = custodian.email if custodian else 'unknown'
    actor_email = actor.email if actor else 'system'
    
    log_message = (
        f"REFERRAL_CUSTODIAN_ASSIGNED | "
        f"original_referrer_id={referrer_id} | "
        f"original_referrer_email={referrer_email} | "
        f"custodian={custodian_email} | "
        f"actor={actor_email} | "
        f"reason={reason or 'Not provided'} | "
        f"timestamp={timezone.now().isoformat()}"
    )
    
    logger.info(log_message)

