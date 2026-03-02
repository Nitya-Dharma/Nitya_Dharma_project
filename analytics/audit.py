"""
Analytics Access Audit Logging

Task 14.2: Analytics Access Logging

Logs all access to analytics data for audit and compliance.
Read-only logging, no mutations.
"""

import logging
from django.contrib.auth import get_user_model
from .models import AnalyticsAccessLog

User = get_user_model()
logger = logging.getLogger(__name__)


def log_analytics_access(
    user: User,
    access_type: str,
    filters_applied: dict = None
):
    """
    Log analytics data access for audit trail.
    
    Task 14.2: Analytics Access Logging
    
    Args:
        user: User who accessed analytics data
        access_type: Type of access (e.g., "api_query", "dashboard_aggregation")
        filters_applied: Optional dictionary of filters/parameters used
    
    Note:
        - All analytics access is logged
        - Used for compliance and security auditing
        - No PII in filters_applied
    """
    try:
        AnalyticsAccessLog.objects.create(
            accessed_by=user,
            access_type=access_type,
            filters_applied=filters_applied or {}
        )
        logger.info(f"Analytics access logged: {user.email} - {access_type}")
    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"Failed to log analytics access: {str(e)}", exc_info=True)
