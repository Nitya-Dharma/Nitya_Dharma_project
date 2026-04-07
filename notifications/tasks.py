import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="notifications.send_notification_task",
    bind=True,
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_notification_task(self, user_id, message):
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(id=user_id)

        logger.info(f"Notification processed for user {user_id}")
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        raise
