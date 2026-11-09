"""
Cross-process Celery email integration tests (GitHub Actions only).

Requires:
  DJANGO_SETTINGS_MODULE=nityadharma.settings.integration_ci
  INTEGRATION_CI_RUN=1
  A live disposable Redis broker
  A Celery worker: celery -A nityadharma worker --pool=solo -Q default,emails
    with INTEGRATION_CI_EMAIL_ROLE=worker
  Disposable MySQL for the legacy password-reset view path only

When settings are integration_ci, missing INTEGRATION_CI_RUN hard-fails
(configuration error). Outside that settings module, these tests SkipTest so
unrelated discovery remains usable.

Does not claim exactly-once delivery. Does not enable ZeptoMail. Does not use
production SMTP/Resend. Does not modify production task code.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest import SkipTest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from accounts.tests.ci_email_backend import (
    count_attempts,
    count_logical_messages_for_corr,
    email_root,
    fail_counter_path,
    make_corr_token,
    wait_for_worker_execution,
)
from core.email_providers import (
    FLOW_PANDIT_ADMIN,
    queue_or_send_transactional_email,
)

_INTEGRATION_SETTINGS = "nityadharma.settings.integration_ci"

# Collection-time hard-fail: under integration_ci, missing RUN must not skip-green.
if os.environ.get("DJANGO_SETTINGS_MODULE", "").strip() == _INTEGRATION_SETTINGS:
    if os.environ.get("INTEGRATION_CI_RUN", "").strip() != "1":
        raise ImproperlyConfigured(
            "INTEGRATION_CI_RUN=1 is required when "
            "DJANGO_SETTINGS_MODULE=nityadharma.settings.integration_ci. "
            "Refusing to silently skip the Celery integration suite."
        )


def _require_integration_ci_runtime() -> None:
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "").strip()
    run_flag = os.environ.get("INTEGRATION_CI_RUN", "").strip()

    # Hard-fail under integration_ci — never SkipTest for this configuration error.
    if settings_module == _INTEGRATION_SETTINGS:
        if run_flag != "1":
            raise ImproperlyConfigured(
                "INTEGRATION_CI_RUN=1 is required when "
                "DJANGO_SETTINGS_MODULE=nityadharma.settings.integration_ci. "
                "Refusing to silently skip the Celery integration suite."
            )
    else:
        # Preserve unrelated test discovery outside integration settings.
        raise SkipTest(
            "Celery integration tests run only with "
            f"DJANGO_SETTINGS_MODULE={_INTEGRATION_SETTINGS} and "
            "INTEGRATION_CI_RUN=1."
        )

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", True):
        raise ImproperlyConfigured(
            "CELERY_TASK_ALWAYS_EAGER must be False for integration CI."
        )
    role = str(getattr(settings, "INTEGRATION_CI_EMAIL_ROLE", "test")).lower()
    if role == "worker":
        raise ImproperlyConfigured(
            "Test process must not use INTEGRATION_CI_EMAIL_ROLE=worker."
        )


def _new_corr() -> str:
    return uuid.uuid4().hex[:16]


def _worker_pid_from_file() -> int | None:
    raw = getattr(
        settings,
        "INTEGRATION_CI_WORKER_PID_FILE",
        os.environ.get(
            "INTEGRATION_CI_WORKER_PID_FILE", "/tmp/celery-integration-worker.pid"
        ),
    )
    path = Path(str(raw))
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    return int(text)


def _assert_worker_not_test(sidecar: dict) -> None:
    test_pid = os.getpid()
    worker_pid = int(sidecar["pid"])
    if worker_pid == test_pid:
        raise AssertionError(
            f"Execution sidecar pid {worker_pid} matches test process; "
            "worker did not execute the send path."
        )
    if sidecar.get("role") != "worker":
        raise AssertionError(f"Unexpected sidecar role: {sidecar!r}")
    file_pid = _worker_pid_from_file()
    if file_pid is None:
        raise AssertionError(
            "Worker PID file missing; cannot cross-check sidecar pid "
            f"(expected {getattr(settings, 'INTEGRATION_CI_WORKER_PID_FILE', '')})."
        )
    if worker_pid != file_pid:
        raise AssertionError(
            f"Sidecar pid {worker_pid} does not match worker PID file {file_pid}."
        )


@override_settings(
    ZEPTOMAIL_ENABLED_FLOWS=frozenset(),
    EMAIL_HOST="",
    EMAIL_HOST_USER="",
    EMAIL_HOST_PASSWORD="",
    RESEND_API_KEY="",
    ZEPTOMAIL_EMAIL_HOST="",
    ZEPTOMAIL_EMAIL_HOST_USER="",
    ZEPTOMAIL_EMAIL_HOST_PASSWORD="",
    ZEPTOMAIL_DEFAULT_FROM_EMAIL="",
)
class ZeptoMailCeleryIntegrationTests(SimpleTestCase):
    """DB-free flows: enqueue via production helpers; assert worker file side effects."""

    databases = set()

    def setUp(self):
        _require_integration_ci_runtime()
        self.corr = _new_corr()
        self.token = make_corr_token(self.corr)
        # Worker and tests must share EMAIL_FILE_PATH from integration_ci env.
        # Isolate cases by unique corr tokens only (not per-process path overrides).
        root = email_root()
        (root / "_executed").mkdir(exist_ok=True)
        (root / "_fail").mkdir(exist_ok=True)
        (root / "_attempts").mkdir(exist_ok=True)

    def _wait(self, min_messages: int = 1):
        result = wait_for_worker_execution(
            self.corr, timeout_seconds=90.0, min_messages=min_messages
        )
        _assert_worker_not_test(result["sidecar"])
        return result

    def test_smoke_registered_task_name_executes_in_worker(self):
        from core.tasks_email import send_email_task

        self.assertEqual(send_email_task.name, "core.send_email_task")
        recipient = f"smoke-{self.token}@example.test"
        async_result = send_email_task.delay(
            f"Smoke {self.token}",
            f"Body marker {self.token}",
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            flow="verification",
        )
        self.assertIsNotNone(async_result.id)
        result = self._wait()
        self.assertGreaterEqual(result["message_count"], 1)
        self.assertEqual(
            count_logical_messages_for_corr(self.corr), result["message_count"]
        )

    def test_verification_helper_enqueues_flow(self):
        from accounts.email_verification import send_verification_email

        user = SimpleNamespace(
            email=f"verify-{self.token}@example.test",
            get_full_name=lambda: f"Verify {self.token}",
        )
        token = SimpleNamespace(token=f"tok-{self.corr}")
        send_verification_email(user, token)
        result = self._wait()
        self.assertGreaterEqual(result["message_count"], 1)
        self.assertIn(user.email, result["sidecar"].get("to", []))

    def test_password_reset_view_send_mail_enqueues_flow(self):
        from accounts.views_password_reset import EnhancedPasswordResetView

        user = SimpleNamespace(
            email=f"reset-{self.token}@example.test",
            get_full_name=lambda: f"Reset {self.token}",
        )
        view = EnhancedPasswordResetView()
        context = {
            "user": user,
            "uid": "MQ",
            "token": f"set-password-{self.corr}",
            "protocol": "http",
            "domain": "testserver",
        }
        view.send_mail(
            "accounts/emails/password_reset_subject.txt",
            "accounts/emails/password_reset_email_simple.html",
            context,
            settings.DEFAULT_FROM_EMAIL,
            user.email,
        )
        result = self._wait()
        self.assertGreaterEqual(result["message_count"], 1)

    def test_password_change_helper_enqueues_flow(self):
        from accounts.views_password_reset import send_password_change_notification

        user = SimpleNamespace(
            email=f"changed-{self.token}@example.test",
            get_full_name=lambda: f"Changed {self.token}",
        )
        send_password_change_notification(user)
        result = self._wait()
        self.assertGreaterEqual(result["message_count"], 1)

    def test_pandit_admin_queue_or_send_mirrors_production_args(self):
        """
        Partial coverage: mirrors pandit_register's queue_or_send args/flow.
        Does not execute the full pandit_register registration path.
        """
        admin_email = f"ops-{self.token}@example.test"
        with override_settings(ADMINS=(("Ops", admin_email),)):
            queue_or_send_transactional_email(
                FLOW_PANDIT_ADMIN,
                "[Nitya Dharma] New Pandit registration",
                f"A new Pandit has registered: pandit-{self.token}@example.test. "
                f"Please review in the admin.",
                settings.DEFAULT_FROM_EMAIL,
                [admin_email],
                fail_silently=True,
            )
        result = self._wait()
        self.assertGreaterEqual(result["message_count"], 1)
        self.assertIn(admin_email, result["sidecar"].get("to", []))

    def test_controlled_retry_before_send_at_least_one(self):
        """
        Force one failure-before-send, then allow success via Celery autoretry.

        Proves >=2 worker attempts and that the fail counter was consumed.
        Does not claim exactly-once delivery (acks_late duplicate risk remains).
        """
        from core.tasks_email import send_email_task

        fail_path = fail_counter_path(self.corr)
        fail_path.write_text("1", encoding="utf-8")
        recipient = f"retry-{self.token}@example.test"
        send_email_task.delay(
            f"Retry {self.token}",
            f"Retry body {self.token}",
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            flow="password_change",
        )
        result = self._wait(min_messages=1)
        self.assertGreaterEqual(result["message_count"], 1)
        self.assertFalse(
            fail_path.exists(),
            "forced fail-before-send counter must be consumed after retry success",
        )
        attempts = count_attempts(self.corr)
        self.assertGreaterEqual(
            attempts,
            2,
            f"expected at least two worker attempts for corr={self.corr}, got {attempts}",
        )
        # Exactly-once is not asserted; duplicates would still pass at-least-one.


@override_settings(
    ZEPTOMAIL_ENABLED_FLOWS=frozenset(),
    EMAIL_HOST="",
    EMAIL_HOST_USER="",
    EMAIL_HOST_PASSWORD="",
    RESEND_API_KEY="",
)
class ZeptoMailCeleryLegacyPasswordResetTests(TestCase):
    """Legacy view path requires disposable MySQL (User lookup)."""

    def setUp(self):
        _require_integration_ci_runtime()
        self.corr = _new_corr()
        self.token = make_corr_token(self.corr)
        root = email_root()
        (root / "_executed").mkdir(exist_ok=True)
        (root / "_fail").mkdir(exist_ok=True)
        (root / "_attempts").mkdir(exist_ok=True)

        User = get_user_model()
        self.email = f"legacy-{self.token}@example.test"
        self.user = User.objects.create_user(
            email=self.email,
            password="IntegrationCiOnly-NotProd-1",
        )
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])

    def test_legacy_password_reset_request_enqueues_flow(self):
        # accounts.views.password_reset_request is the production caller; it is
        # not currently mounted in accounts/urls.py, so invoke the view callable
        # directly (still the real function, no browser).
        from accounts.views import password_reset_request

        factory = RequestFactory()
        request = factory.post(
            "/accounts/password-reset-request/",
            data={"email": self.email},
        )
        request.user = AnonymousUser()
        # messages.* used by the view
        request.session = {}
        request._messages = FallbackStorage(request)

        response = password_reset_request(request)
        self.assertEqual(getattr(response, "status_code", 200), 200)
        result = wait_for_worker_execution(self.corr, timeout_seconds=90.0)
        _assert_worker_not_test(result["sidecar"])
        self.assertGreaterEqual(result["message_count"], 1)
