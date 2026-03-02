"""
Service functions for displaying audit logs with inactive actors.

TASK 28: Audit Logs Referencing Removed Actors

This module provides functions to:
- Get actor display name (handling inactive actors)
- Format audit log entries for display
- Ensure no broken references
"""

import logging
from typing import Optional
from .models_audit_log import AuditLog

logger = logging.getLogger(__name__)


def get_actor_display_name(audit_log: AuditLog) -> str:
    """
    TASK 28: Get display name for audit log actor, handling inactive actors.
    
    Args:
        audit_log: AuditLog instance
    
    Returns:
        str: Display name for actor
    """
    # If actor is active, use current name
    if audit_log.actor and audit_log.actor.is_active and audit_log.actor.status != 'deactivated':
        return audit_log.actor.get_full_name() or audit_log.actor.email
    
    # If actor is deactivated, use immutable snapshot
    if audit_log.actor_display_name:
        return f"{audit_log.actor_display_name} (Inactive)"
    
    # If actor is None but we have display name
    if audit_log.actor_display_name:
        return f"{audit_log.actor_display_name} (Inactive)"
    
    # Fallback
    if audit_log.actor:
        return f"{audit_log.actor.email} (Inactive)"
    
    return "System"


def format_audit_log_entry(audit_log: AuditLog) -> dict:
    """
    TASK 28: Format audit log entry for display.
    
    Args:
        audit_log: AuditLog instance
    
    Returns:
        dict: Formatted audit log entry
    """
    return {
        'id': audit_log.id,
        'public_id': audit_log.public_id,
        'action_type': audit_log.action_type,
        'actor_display': get_actor_display_name(audit_log),
        'actor_role': audit_log.actor_role,
        'target_entity_type': audit_log.target_entity_type,
        'target_entity_id': audit_log.target_entity_id,
        'target_entity_public_id': audit_log.target_entity_public_id,
        'metadata': audit_log.metadata,
        'created_at': audit_log.created_at.isoformat(),
        'is_actor_inactive': (
            audit_log.actor is None or
            not audit_log.actor.is_active or
            audit_log.actor.status == 'deactivated'
        )
    }







