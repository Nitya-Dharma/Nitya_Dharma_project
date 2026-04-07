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
def send_email_task(self, subject, message, from_email, recipient_list):
    from django.core.mail import send_mail

    try:
        send_mail(subject, message, from_email, recipient_list)
        logger.info(f"Email sent to {recipient_list}")
    except Exception as e:
        logger.error(f"Email failed: {e}")
        raise
