"""
Celery transactional email task.

Registered name: core.send_email_task (see @shared_task name=).
Routed to queue 'emails' via CELERY_TASK_ROUTES['core.send_email_task'].

Retries: autoretry_for Exception, max_retries=3, retry_backoff=True.
Soft time limit 20s / hard 30s.

A valid transactional flow ID is mandatory. Missing/blank/unknown flows are
rejected before send. flow=None cannot select Gmail.

Delivery: at-least-once enqueue + retries; SMTP/Celery cannot guarantee
exactly-once delivery. Do not log recipients, passwords, tokens, or full URLs.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="core.send_email_task",
    ignore_result=True,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    time_limit=30,
    soft_time_limit=20,
)
def send_email_task(self, subject, message, from_email, recipient_list, flow=None):
    """
    Transactional email task — requires a known flow ID.

    Provider is resolved from ZEPTOMAIL_ENABLED_FLOWS for that flow
    (empty allowlist = explicit Gmail/SMTP rollback). ZeptoMail failure
    never falls back to Gmail inside this task.
    """
    from core.email_providers import require_known_transactional_flow, send_for_flow

    flow_id = require_known_transactional_flow(flow)
    # Materialize once so a generator/iterable is not consumed before send.
    recipients = list(recipient_list) if recipient_list is not None else []
    recipient_count = len(recipients)
    try:
        send_for_flow(
            flow_id,
            subject,
            message,
            from_email,
            recipients,
            fail_silently=False,
        )
        logger.info(
            "Email task succeeded flow=%s recipient_count=%s",
            flow_id,
            recipient_count,
        )
    except Exception as e:
        logger.error(
            "Email task failed flow=%s error_type=%s",
            flow_id,
            type(e).__name__,
        )
        raise
