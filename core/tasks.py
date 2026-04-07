import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    time_limit=30,
    soft_time_limit=20,
)
def debug_task(self):
    logger.info('Celery is working')


# Registers send_email_task with Celery (autodiscover only imports core.tasks).
from core.tasks_email import send_email_task  # noqa: E402,F401
