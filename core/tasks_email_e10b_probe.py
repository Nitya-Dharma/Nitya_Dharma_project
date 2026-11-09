"""
E10B probe-only Celery email task.

NOT for production. NOT a replacement for core.send_email_task.

Registered only when worker-probe E10B settings set CELERY_IMPORTS to this module.
Never imported from core.tasks (autodiscover) so production workers do not load it.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="core.send_email_task_e10b_probe",
    ignore_result=True,
    bind=True,
    max_retries=0,
    time_limit=30,
    soft_time_limit=20,
)
def send_email_task_e10b_probe(self, subject, message, from_email, recipient_list):
    """
    One-shot filebased/SMTP-agnostic send for isolated worker verification.

    - No autoretry_for / retry_kwargs / self.retry().
    - Does not call core.send_email_task.
    - Does not access models or the database.
    - Does not implement synchronous fallback.
    """
    from django.core.mail import send_mail

    # Do not log credentials or full message bodies.
    logger.info(
        "E10B probe task executing: to_count=%s subject_len=%s",
        len(recipient_list) if recipient_list is not None else 0,
        len(subject) if subject is not None else 0,
    )
    return send_mail(subject, message, from_email, recipient_list)
