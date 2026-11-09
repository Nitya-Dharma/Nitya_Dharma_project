"""
E10B one-shot producer for core.send_email_task_e10b_probe.

Submits exactly one .delay() under E10B worker-probe settings.
Does not start a worker, does not call send_mail, does not use production task.
Does not prove worker completion — use probe_e10b_assert_email_file.py for that.

Require before Django / nityadharma import:
  DJANGO_SETTINGS_MODULE=nityadharma.e10b_worker_probe_settings
  CELERY_BROKER_URL / CELERY_RESULT_BACKEND / ZEPTOMAIL_WORKER_PROBE_EMAIL_DIR

Run (CI / authorized environments only):
  python nityadharma/probe_e10b_celery_worker_producer.py
"""

from __future__ import annotations

import os
import sys


EXPECTED_SETTINGS = "nityadharma.e10b_worker_probe_settings"
REFUSING_ENGINE = "nityadharma.e10b_refusing_db"
PROBE_TASK_NAME = "core.send_email_task_e10b_probe"
PROD_TASK_NAME = "core.send_email_task"

RECIPIENT = "e10b-worker-test@example.invalid"
SUBJECT = "Nitya Dharma E10B Celery Worker Test"
BODY = (
    "This is an isolated Celery worker execution test. "
    "No SMTP delivery is intended."
)
FROM_EMAIL = "worker-probe@nityadharma.invalid"


class ProducerRefusal(Exception):
    pass


def _fail(msg: str) -> None:
    raise ProducerRefusal(msg)


def _prepare_sys_path() -> None:
    script_dir = os.path.abspath(os.path.dirname(__file__))
    worktree_root = os.path.abspath(os.path.join(script_dir, ".."))
    sys.path[:] = [p for p in sys.path if os.path.abspath(p) != script_dir]
    if worktree_root not in sys.path:
        sys.path.insert(0, worktree_root)


def main() -> int:
    print("E10B producer: validating environment (no worker start; one delay only)")
    _prepare_sys_path()

    configured = os.environ.get("DJANGO_SETTINGS_MODULE", "").strip()
    if configured != EXPECTED_SETTINGS:
        _fail(
            f"DJANGO_SETTINGS_MODULE must be {EXPECTED_SETTINGS!r} before import "
            f"(got {configured!r})."
        )

    for name in ("DATABASE_URL", "MYSQL_URL", "REDIS_URL", "RESEND_API_KEY"):
        if os.environ.get(name, "").strip():
            _fail(f"{name} must not be set (value not shown).")

    for name in (
        "CELERY_BROKER_URL",
        "CELERY_RESULT_BACKEND",
        "ZEPTOMAIL_WORKER_PROBE_EMAIL_DIR",
    ):
        if not os.environ.get(name, "").strip():
            _fail(f"Missing required environment variable {name}.")

    if not RECIPIENT.endswith(".invalid"):
        _fail("Recipient must end with .invalid")

    # Import Django only after settings-module gate (avoids wrong default selection).
    import django
    from django.conf import settings

    django.setup()

    if settings.SETTINGS_MODULE != EXPECTED_SETTINGS:
        _fail(f"settings.SETTINGS_MODULE={settings.SETTINGS_MODULE!r}")

    engine = settings.DATABASES["default"]["ENGINE"]
    if engine != REFUSING_ENGINE:
        _fail(f"Expected refusing ENGINE {REFUSING_ENGINE!r}, got {engine!r}")

    from django.db import connections

    if connections["default"].connection is not None:
        _fail("Database connection is open; refusing to proceed")

    backend = settings.EMAIL_BACKEND
    if "filebased" not in backend:
        _fail(f"EMAIL_BACKEND must be filebased for E10B, got {backend!r}")
    if "smtp" in backend.lower():
        _fail("SMTP email backend is forbidden for E10B producer")

    if settings.CELERY_TASK_ALWAYS_EAGER:
        _fail("CELERY_TASK_ALWAYS_EAGER must be False for real worker test")

    if not settings.CELERY_BROKER_URL:
        _fail("CELERY_BROKER_URL must be explicitly configured")

    imports = tuple(getattr(settings, "CELERY_IMPORTS", ()) or ())
    if "core.tasks_email_e10b_probe" not in imports:
        _fail("CELERY_IMPORTS must include core.tasks_email_e10b_probe")

    from core.tasks_email_e10b_probe import send_email_task_e10b_probe
    from core.tasks_email import send_email_task as production_send_email_task

    if send_email_task_e10b_probe.name != PROBE_TASK_NAME:
        _fail(f"Unexpected probe task name {send_email_task_e10b_probe.name!r}")
    if production_send_email_task.name != PROD_TASK_NAME:
        _fail("Production task name unexpected; aborting for safety")

    if send_email_task_e10b_probe is production_send_email_task:
        _fail("Probe task unexpectedly aliased to production task")

    max_retries = getattr(send_email_task_e10b_probe, "max_retries", None)
    autoretry = getattr(send_email_task_e10b_probe, "autoretry_for", ())
    if max_retries not in (0, None) and max_retries != 0:
        _fail(f"Probe task max_retries must be 0, got {max_retries!r}")
    if autoretry:
        _fail(f"Probe task must not set autoretry_for, got {autoretry!r}")

    async_result = send_email_task_e10b_probe.delay(
        SUBJECT,
        BODY,
        FROM_EMAIL,
        [RECIPIENT],
    )

    print("E10B producer: submitted exactly one probe task")
    print("  NOTE: submission is not worker completion; CI assert step verifies file")
    print(f"  settings_module={settings.SETTINGS_MODULE}")
    print(f"  task_name={send_email_task_e10b_probe.name}")
    print(f"  task_id={async_result.id}")
    print(f"  queue_hint=emails")
    print(f"  recipient={RECIPIENT}")
    print(f"  subject={SUBJECT}")
    print(f"  email_backend={settings.EMAIL_BACKEND}")
    print(f"  db_engine={engine}")
    print(f"  db_connection_is_none={connections['default'].connection is None}")
    print("  production_task_invoked=False")
    print("  send_mail_direct=False")
    print("  fallback=False")
    print("  submission_count=1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProducerRefusal as exc:
        print(f"E10B producer REFUSED: {exc}")
        raise SystemExit(2) from exc
