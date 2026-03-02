"""
Referral Auto-Expiry Task (TASK 8: Auto-Expiry Job)

This module contains scheduled tasks for automatic referral expiry management.
"""

import logging
from django.utils import timezone
from django.db import transaction
from .models import ReferralLink
from .constants import AUDIT_ACTION_REFERRAL_EXPIRED, REFERRAL_STATUS_EXPIRED

logger = logging.getLogger(__name__)


def expire_referrals():
    """
    Mark expired referrals as status='expired'.
    
    TASK 8: Auto-expiry job
    
    Rules:
    - Runs daily (can be scheduled via Django-Q or Celery)
    - Marks referrals with expires_at < now() as expired
    - Only updates status, no deletions
    - Logs audit event for each expired referral
    """
    try:
        now = timezone.now()
        
        # Find all active referrals that have expired
        expired_referrals = ReferralLink.objects.filter(
            status=ReferralLink.STATUS_ACTIVE,
            expires_at__lt=now
        )
        
        expired_count = 0
        
        with transaction.atomic():
            for referral in expired_referrals:
                old_status = referral.status
                referral.status = REFERRAL_STATUS_EXPIRED
                referral.is_active = False  # Also deactivate
                referral.save(update_fields=['status', 'is_active'])
                
                # TASK 8 & 9: Log audit event
                try:
                    from analytics.audit_events import log_audit_event
                    log_audit_event(
                        event_type=AUDIT_ACTION_REFERRAL_EXPIRED,
                        user=referral.created_by,  # Referrer
                        metadata={
                            'referral_link_id': referral.id,
                            'token': referral.token[:8] + '...',
                            'expires_at': referral.expires_at.isoformat(),
                            'old_status': old_status,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log audit event for expired referral {referral.id}: {str(e)}")
                
                expired_count += 1
        
        logger.info(f"Expired {expired_count} referral(s) at {now}")
        return expired_count
        
    except Exception as e:
        logger.error(f"Error expiring referrals: {str(e)}", exc_info=True)
        raise


# For Django-Q or Celery scheduling:
# @periodic_task(run_every=crontab(hour=0, minute=0))  # Run daily at midnight
# def expire_referrals_task():
#     expire_referrals()

