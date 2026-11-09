import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="core.send_email_task",
    ignore_result=True,
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    time_limit=30,
    soft_time_limit=20,
)
def send_email_task(self, subject, message, from_email, recipient_list, flow=None):
    """
    Transactional email task.

    Backward compatible: existing callers omit flow → default provider
    (Gmail / Resend / SMTP via Django EMAIL_*).

    When flow= is provided, provider is resolved centrally from
    ZEPTOMAIL_ENABLED_FLOWS (empty allowlist → default).
    """
    from core.email_providers import send_for_flow

    try:
        send_for_flow(
            flow,
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email sent to {recipient_list}")
    except Exception as e:
        logger.error(f"Email failed: {e}")
        raise
