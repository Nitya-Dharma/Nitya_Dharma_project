import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True, autoretry_for=(Exception,), retry_backoff=True)
def log_analytics_task(self, data):
    try:
        logger.info(f"Analytics event stored: {data.get('event_type')}")
        event_type = data.get("event_type")
        if not event_type:
            return
        from django.contrib.auth import get_user_model
        from behavior_engine.models import UserBehaviorEvent

        User = get_user_model()
        uid = None
        uid_pk = data.get("user_id")
        if uid_pk is not None:
            try:
                uid = User.objects.get(pk=uid_pk)
            except User.DoesNotExist:
                uid = None

        UserBehaviorEvent.objects.create(
            event_type=event_type,
            user=uid,
            session_id=data.get("session_id"),
            object_type=data.get("object_type"),
            object_id=data.get("object_id"),
            metadata=data.get("metadata") or {},
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
        )
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        raise
