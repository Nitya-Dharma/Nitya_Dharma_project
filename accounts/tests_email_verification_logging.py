"""Email-verification logs must not contain the verification secret or its URL."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase, override_settings

from accounts.email_verification import (
    create_email_verification,
    send_verification_email,
    verify_email,
)
from accounts.models import EmailVerificationToken
from accounts.views_email_verification import verify_email_view

User = get_user_model()
_SECRET = "A" * 64


def _record_blob(record) -> str:
    blob = repr(record.__dict__)
    if record.exc_info:
        blob += repr(record.exc_info)
    return blob


def _assert_secret_absent(test_case, captured, secret: str) -> None:
    rendered = "\n".join(captured.output)
    test_case.assertNotIn(secret, rendered)
    test_case.assertNotIn("/accounts/verify-email/" + secret, rendered)
    for record in captured.records:
        blob = _record_blob(record)
        test_case.assertNotIn(secret, blob)
        test_case.assertNotIn("/accounts/verify-email/" + secret, blob)


def _request():
    request = RequestFactory().get("/verify/")
    request.session = SessionStore()
    request._messages = FallbackStorage(request)
    return request


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailVerificationLogRedactionTests(TestCase):
    def test_token_creation_does_not_log_the_secret(self):
        user = User.objects.create_user(
            email="log-redaction@example.test",
            password="isolated-test-password",
            role="user",
            status="active",
            is_active=True,
        )
        with self.assertLogs("accounts.email_verification", level="INFO") as captured:
            token = create_email_verification(user)

        self.assertTrue(token.token)
        self.assertEqual(len(token.token), 64)
        _assert_secret_absent(self, captured, token.token)
        self.assertTrue(
            any("token created" in record.getMessage() for record in captured.records)
        )

    def test_token_creation_failure_does_not_log_the_exception_secret(self):
        user = User.objects.create_user(
            email="log-redaction-fail@example.test",
            password="isolated-test-password",
            role="user",
            status="active",
            is_active=True,
        )
        with patch.object(
            EmailVerificationToken.objects,
            "create",
            side_effect=RuntimeError(_SECRET),
        ):
            with self.assertLogs("accounts.email_verification", level="ERROR") as captured:
                with self.assertRaises(RuntimeError):
                    create_email_verification(user)
        _assert_secret_absent(self, captured, _SECRET)

    def test_send_does_not_log_token_or_url(self):
        user = User.objects.create_user(
            email="log-redaction-send@example.test",
            password="isolated-test-password",
            role="user",
            status="active",
            is_active=True,
        )
        token = EmailVerificationToken.objects.create(user=user)
        with patch("core.tasks_email.send_email_task") as task:
            task.delay.return_value = None
            with self.assertLogs("accounts.email_verification", level="INFO") as captured:
                send_verification_email(user, token)
        _assert_secret_absent(self, captured, token.token)

    def test_send_failure_does_not_log_exception_text(self):
        user = User.objects.create_user(
            email="log-redaction-send-fail@example.test",
            password="isolated-test-password",
            role="user",
            status="active",
            is_active=True,
        )
        token = EmailVerificationToken.objects.create(user=user)
        leaked_text = token.token + " /accounts/verify-email/" + token.token
        leaked = RuntimeError(leaked_text)
        with patch("core.tasks_email.send_email_task") as task, patch(
            "accounts.email_verification.send_mail",
            side_effect=leaked,
        ) as direct_send:
            task.delay.side_effect = leaked
            with self.assertLogs("accounts.email_verification", level="ERROR") as captured:
                with self.assertRaises(RuntimeError) as raised:
                    send_verification_email(user, token)
        task.delay.assert_called_once()
        direct_send.assert_called_once()
        self.assertEqual(str(raised.exception), leaked_text)
        _assert_secret_absent(self, captured, token.token)
        rendered = "\n".join(captured.output)
        self.assertNotIn(leaked_text, rendered)
        for record in captured.records:
            self.assertNotIn(leaked_text, _record_blob(record))
        self.assertTrue(
            any(getattr(record, "error_type", None) == "RuntimeError" for record in captured.records)
        )

    def test_verify_failure_does_not_log_the_secret(self):
        user = User.objects.create_user(
            email="log-redaction-verify-fail@example.test",
            password="isolated-test-password",
            role="user",
            status="active",
            is_active=True,
        )
        token = EmailVerificationToken.objects.create(user=user)
        leaked_text = token.token + " /accounts/verify-email/" + token.token
        leaked = RuntimeError(leaked_text)
        with patch.object(EmailVerificationToken, "save", side_effect=leaked):
            with self.assertLogs("accounts.email_verification", level="ERROR") as captured:
                with self.assertRaises(RuntimeError) as raised:
                    verify_email(token.token)
        self.assertEqual(str(raised.exception), leaked_text)
        _assert_secret_absent(self, captured, token.token)
        rendered = "\n".join(captured.output)
        self.assertNotIn(leaked_text, rendered)
        for record in captured.records:
            self.assertNotIn(leaked_text, _record_blob(record))
        self.assertTrue(
            any(getattr(record, "error_type", None) == "RuntimeError" for record in captured.records)
        )

    def test_verify_view_does_not_log_token_prefix_or_secret(self):
        request = _request()
        with patch(
            "accounts.views_email_verification.verify_email",
            side_effect=ValidationError("Invalid verification token"),
        ):
            with self.assertLogs("accounts.views_email_verification", level="INFO") as captured:
                response = verify_email_view(request, _SECRET)
        self.assertEqual(response.status_code, 302)
        _assert_secret_absent(self, captured, _SECRET)
        self.assertNotIn(_SECRET[:20], "\n".join(captured.output))
        for record in captured.records:
            self.assertNotIn(_SECRET[:20], _record_blob(record))

    def test_unexpected_verify_view_error_does_not_expose_exception_text(self):
        request = _request()
        leaked_text = "internal failure " + _SECRET
        with patch(
            "accounts.views_email_verification.verify_email",
            side_effect=RuntimeError(leaked_text),
        ):
            with self.assertLogs(
                "accounts.views_email_verification", level="ERROR"
            ) as captured:
                response = verify_email_view(request, _SECRET)
        self.assertEqual(response.status_code, 302)
        message_text = " ".join(str(message) for message in request._messages)
        self.assertNotIn(leaked_text, message_text)
        self.assertNotIn(_SECRET, message_text)
        _assert_secret_absent(self, captured, _SECRET)
        self.assertNotIn(leaked_text, "\n".join(captured.output))
