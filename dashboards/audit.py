"""
Super Admin Action Logging (UNIT 6).

Hooks into existing audit infrastructure to log all Super Admin actions.
Every Super Admin action must itself be audited.
"""
import logging
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


def log_super_admin_action(action_type, target_entity=None, before_snapshot=None, after_snapshot=None, actor=None, additional_data=None):
    """
    Log a Super Admin action for audit purposes (UNIT 6).
    
    This function logs Super Admin actions to:
    1. Django logging system (immediate)
    2. Database audit tables (if applicable)
    
    Args:
        action_type (str): Type of action (e.g., 'PAGE_EDIT', 'PANDIT_STATUS_CHANGE', 'CONFIG_UPDATE')
        target_entity: Model instance that was modified (optional)
        before_snapshot (dict): State before action (optional)
        after_snapshot (dict): State after action (optional)
        actor (User): Super Admin user who performed the action
        additional_data (dict): Any additional context (optional)
    
    Returns:
        None
    """
    if not actor or not actor.is_superuser:
        logger.warning(f"log_super_admin_action called for non-superuser: {actor}")
        return
    
    entity_type = target_entity.__class__.__name__ if target_entity else 'Unknown'
    entity_id = getattr(target_entity, 'pk', 'unknown') if target_entity else 'unknown'
    actor_email = actor.email if actor else 'system'
    
    # Build log message
    log_message = (
        f"SUPER_ADMIN_ACTION | "
        f"action={action_type} | "
        f"entity_type={entity_type} | "
        f"entity_id={entity_id} | "
        f"actor={actor_email} | "
        f"timestamp={timezone.now().isoformat()}"
    )
    
    if before_snapshot:
        log_message += f" | before={before_snapshot}"
    if after_snapshot:
        log_message += f" | after={after_snapshot}"
    if additional_data:
        log_message += f" | additional={additional_data}"
    
    logger.info(log_message)
    
    # Store in database audit table if applicable
    # For Page edits, use PageAuditLog
    if target_entity and entity_type == 'Page':
        from pages.models import PageAuditLog, Page
        from pages.constants import AUDIT_ACTION_UPDATE
        
        try:
            PageAuditLog.objects.create(
                page=target_entity,
                action=AUDIT_ACTION_UPDATE,
                performed_by=actor,
            )
        except Exception as e:
            logger.error(f"Failed to create PageAuditLog entry: {str(e)}")
    
    # TODO: Add audit logging for other entity types (Pandit status changes, Config updates)
    # This can be extended as needed when those actions are implemented





















