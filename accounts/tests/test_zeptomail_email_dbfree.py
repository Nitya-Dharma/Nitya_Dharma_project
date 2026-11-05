"""
Database-free unit tests for Phase 2D ZeptoMail email recipient behavior.

Uses Django SimpleTestCase only (no DB). Run with unittest after django.setup(),
not manage.py test, so no test database is created.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core import mail
from django.test import SimpleTestCase, override_settings


def _expert_admin_recipient():
    """Same resolution as services.views_expert_ui Phase 2D block."""
    return (
        getattr(settings, "ADMIN_NOTIFICATION_EMAIL", "") or ""
    ).strip() or settings.DEFAULT_FROM_EMAIL


def _pandit_admin_recipients():
    """Same resolution as accounts.views Phase 2D pandit admin block."""
    admin_notify = (
        getattr(settings, "ADMIN_NOTIFICATION_EMAIL", "") or ""
    ).strip()
    if admin_notify:
        return [admin_notify]
    admins = getattr(settings, "ADMINS", ())
    return [email for _, email in admins] if admins else []


def _invoke_expert_admin_alert(name, phone, normalized_type):
    """Invoke expert admin alert using the same send_mail import as the view."""
    from services.views_expert_ui import send_mail as expert_send_mail

    _admin_to = _expert_admin_recipient()
    expert_send_mail(
        subject="New Expert Registration",
        message=(
            f"A new expert has registered.\n\n"
            f"Name: {name}\nPhone: {phone}\nType: {normalized_type}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[_admin_to],
        fail_silently=True,
    )


def _invoke_pandit_admin_alert(user_email):
    """Invoke pandit admin alert paths mirroring accounts.views Phase 2D."""
    from django.core.mail import send_mail

    recipient_list = _pandit_admin_recipients()
    if not (recipient_list and user_email):
        return "skipped"
    try:
        from core.tasks_email import send_email_task

        send_email_task.delay(
            "[Nitya Dharma] New Pandit registration",
            f"A new Pandit has registered: {user_email}. Please review in the admin.",
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
        )
        return "celery"
    except Exception:
        send_mail(
            subject="[Nitya Dharma] New Pandit registration",
            message=(
                f"A new Pandit has registered: {user_email}. "
                f"Please review in the admin."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=True,
        )
        return "fallback"


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_HOST="",
    EMAIL_HOST_USER="",
    EMAIL_HOST_PASSWORD="",
    DEFAULT_FROM_EMAIL="noreply@example.test",
    ADMIN_NOTIFICATION_EMAIL="admin-notify@example.test",
    SITE_URL="http://127.0.0.1:8000",
    CELERY_TASK_ALWAYS_EAGER=True,
)
class ZeptoMailEmailDbFreeTests(SimpleTestCase):
    """Must remain SimpleTestCase — no database aliases."""

    databases = set()

    def setUp(self):
        mail.outbox.clear()
        # Guard: this suite must never opt into a DB.
        self.assertEqual(self.__class__.databases, set())

    def test_phase2d_source_still_contains_admin_recipient_logic(self):
        from accounts.views import pandit_register
        from services.views_expert_ui import expert_register_page

        expert_src = inspect.getsource(expert_register_page)
        pandit_src = inspect.getsource(pandit_register)
        self.assertIn("ADMIN_NOTIFICATION_EMAIL", expert_src)
        self.assertIn("DEFAULT_FROM_EMAIL", expert_src)
        self.assertIn("New Expert Registration", expert_src)
        self.assertIn("Set Your Password", expert_src)
        self.assertIn("recipient_list=[email]", expert_src)
        self.assertIn("ADMIN_NOTIFICATION_EMAIL", pandit_src)
        self.assertIn("ADMINS", pandit_src)
        self.assertIn("[Nitya Dharma] New Pandit registration", pandit_src)

    @patch("services.views_expert_ui.send_mail")
    def test_expert_admin_uses_admin_notification_email(self, mock_send):
        _invoke_expert_admin_alert("Ada", "9999999999", "astrologer")
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["subject"], "New Expert Registration")
        self.assertIn("Ada", kwargs["message"])
        self.assertIn("9999999999", kwargs["message"])
        self.assertIn("astrologer", kwargs["message"])
        self.assertEqual(kwargs["from_email"], "noreply@example.test")
        self.assertEqual(kwargs["recipient_list"], ["admin-notify@example.test"])
        self.assertTrue(kwargs["fail_silently"])

    @override_settings(ADMIN_NOTIFICATION_EMAIL="")
    @patch("services.views_expert_ui.send_mail")
    def test_expert_admin_falls_back_to_default_from(self, mock_send):
        _invoke_expert_admin_alert("Bob", "8888888888", "numerologist")
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["recipient_list"], ["noreply@example.test"])
        self.assertEqual(kwargs["from_email"], "noreply@example.test")

    def test_expert_password_email_targets_expert_address_in_source(self):
        from services.views_expert_ui import expert_register_page

        src = inspect.getsource(expert_register_page)
        # Password setup mail must keep the expert address, not admin.
        self.assertIn('subject="Set Your Password"', src)
        self.assertIn("recipient_list=[email]", src)

    @patch("core.tasks_email.send_email_task.delay")
    def test_pandit_admin_prefers_admin_notification_email(self, mock_delay):
        path = _invoke_pandit_admin_alert("pandit@example.test")
        self.assertEqual(path, "celery")
        mock_delay.assert_called_once()
        args = mock_delay.call_args.args
        self.assertEqual(args[0], "[Nitya Dharma] New Pandit registration")
        self.assertIn("pandit@example.test", args[1])
        self.assertEqual(args[2], "noreply@example.test")
        self.assertEqual(args[3], ["admin-notify@example.test"])

    @override_settings(ADMIN_NOTIFICATION_EMAIL="", ADMINS=(("Ops", "ops@example.test"),))
    @patch("core.tasks_email.send_email_task.delay")
    def test_pandit_admin_falls_back_to_admins(self, mock_delay):
        path = _invoke_pandit_admin_alert("pandit2@example.test")
        self.assertEqual(path, "celery")
        self.assertEqual(mock_delay.call_args.args[3], ["ops@example.test"])

    @override_settings(ADMIN_NOTIFICATION_EMAIL="", ADMINS=())
    @patch("core.tasks_email.send_email_task.delay")
    @patch("django.core.mail.send_mail")
    def test_pandit_admin_empty_recipients_skips_send(self, mock_send, mock_delay):
        path = _invoke_pandit_admin_alert("pandit3@example.test")
        self.assertEqual(path, "skipped")
        mock_delay.assert_not_called()
        mock_send.assert_not_called()

    @patch("core.tasks_email.send_email_task.delay", side_effect=RuntimeError("no broker"))
    @patch("django.core.mail.send_mail")
    def test_pandit_admin_fallback_send_mail_path(self, mock_send, mock_delay):
        path = _invoke_pandit_admin_alert("pandit4@example.test")
        self.assertEqual(path, "fallback")
        mock_delay.assert_called_once()
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["subject"], "[Nitya Dharma] New Pandit registration")
        self.assertEqual(kwargs["recipient_list"], ["admin-notify@example.test"])
        self.assertTrue(kwargs["fail_silently"])

    @patch("django.core.mail.send_mail")
    def test_send_email_task_invokes_send_mail_in_process(self, mock_send):
        from core.tasks_email import send_email_task

        # Celery bind=True: first arg is task instance when called as .run()
        send_email_task.run(
            "Task Subject",
            "Task body",
            "from@example.test",
            ["to@example.test"],
        )
        mock_send.assert_called_once_with(
            "Task Subject",
            "Task body",
            "from@example.test",
            ["to@example.test"],
        )

    @patch("core.tasks_email.send_email_task.delay", side_effect=RuntimeError("no broker"))
    @patch("accounts.email_verification.send_mail", return_value=1)
    def test_send_verification_email_with_fake_user_token(self, mock_send, mock_delay):
        from accounts.email_verification import send_verification_email

        user = MagicMock()
        user.email = "user@example.test"
        user.get_full_name.return_value = "Test User"
        token = SimpleNamespace(token="abc123verificationtoken")

        send_verification_email(user, token)

        mock_delay.assert_called_once()
        # delay failed → fallback send_mail (module-local import)
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["subject"], "Verify your email address - Nitya Dharma")
        self.assertEqual(kwargs["from_email"], "noreply@example.test")
        self.assertEqual(kwargs["recipient_list"], ["user@example.test"])
        self.assertIn("abc123verificationtoken", kwargs["message"])
        self.assertIn("Test User", kwargs["message"])

    @patch("core.tasks_email.send_email_task.delay")
    def test_password_change_notification_with_fake_user(self, mock_delay):
        from accounts.views_password_reset import send_password_change_notification

        user = MagicMock()
        user.email = "changed@example.test"
        user.get_full_name.return_value = "Changed User"

        send_password_change_notification(user)

        mock_delay.assert_called_once()
        args = mock_delay.call_args.args
        self.assertEqual(args[0], "Password Changed - Nitya Dharma")
        self.assertIn("Changed User", args[1])
        self.assertEqual(args[2], "noreply@example.test")
        self.assertEqual(args[3], ["changed@example.test"])

    @patch("core.tasks_email.send_email_task.delay", side_effect=RuntimeError("no broker"))
    @patch("accounts.views_password_reset.django_send_mail")
    def test_password_reset_view_send_mail_override(self, mock_send, mock_delay):
        from accounts.views_password_reset import EnhancedPasswordResetView

        user = MagicMock()
        user.email = "reset@example.test"
        user.get_full_name.return_value = "Reset User"
        view = EnhancedPasswordResetView()
        context = {
            "user": user,
            "uid": "MQ",
            "token": "set-password-token",
            "protocol": "http",
            "domain": "127.0.0.1:8000",
        }
        view.send_mail(
            "accounts/emails/password_reset_subject.txt",
            "accounts/emails/password_reset_email_simple.html",
            context,
            "noreply@example.test",
            "reset@example.test",
        )
        mock_delay.assert_called_once()
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["from_email"], "noreply@example.test")
        self.assertEqual(kwargs["recipient_list"], ["reset@example.test"])
        self.assertIn("set-password-token", kwargs["message"])
        self.assertIn("Reset User", kwargs["message"])
        self.assertNotIn("admin-notify@example.test", kwargs["recipient_list"])
