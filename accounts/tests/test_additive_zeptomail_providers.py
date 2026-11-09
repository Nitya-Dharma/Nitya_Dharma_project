"""
Focused tests for additive ZeptoMail (Gmail/default preserved).

Run (no MySQL client required):
  set DJANGO_SETTINGS_MODULE=accounts.tests.additive_email_test_settings
  python -m unittest accounts.tests.test_additive_zeptomail_providers -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from core.email_providers import (
    FLOW_VERIFICATION,
    PROVIDER_DEFAULT,
    PROVIDER_ZEPTOMAIL,
    queue_or_send_transactional_email,
    resolve_provider_for_flow,
    send_for_flow,
    send_via_provider,
    zeptomail_settings_complete,
)
from nityadharma.settings._zeptomail_env import parse_zeptomail_enabled_flows


# Unmistakable test-only placeholder (not a real credential).
_TEST_ONLY_ZEPTOMAIL_PASSWORD = "TEST_ONLY_ZEPTOMAIL_PASSWORD"

_ZEPTO_COMPLETE = dict(
    ZEPTOMAIL_EMAIL_HOST="smtp.zeptomail.in",
    ZEPTOMAIL_EMAIL_PORT=587,
    ZEPTOMAIL_EMAIL_USE_TLS=True,
    ZEPTOMAIL_EMAIL_USE_SSL=False,
    ZEPTOMAIL_EMAIL_HOST_USER="emailapikey",
    ZEPTOMAIL_EMAIL_HOST_PASSWORD=_TEST_ONLY_ZEPTOMAIL_PASSWORD,
    ZEPTOMAIL_DEFAULT_FROM_EMAIL="no-reply@nityadharma.com",
    ZEPTOMAIL_EMAIL_TIMEOUT=10,
)


class ParseAllowlistTests(SimpleTestCase):
    databases = set()

    def test_empty_allowlist(self):
        self.assertEqual(parse_zeptomail_enabled_flows(""), frozenset())
        self.assertEqual(parse_zeptomail_enabled_flows(None), frozenset())
        self.assertEqual(parse_zeptomail_enabled_flows("  , , "), frozenset())

    def test_parses_flows(self):
        self.assertEqual(
            parse_zeptomail_enabled_flows("verification, password_reset"),
            frozenset({"verification", "password_reset"}),
        )


class ResolveProviderTests(SimpleTestCase):
    databases = set()

    def test_empty_allowlist_always_default(self):
        self.assertEqual(resolve_provider_for_flow(None), PROVIDER_DEFAULT)
        self.assertEqual(resolve_provider_for_flow(FLOW_VERIFICATION), PROVIDER_DEFAULT)

    @override_settings(ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}))
    def test_allowlisted_flow_selects_zeptomail(self):
        self.assertEqual(resolve_provider_for_flow(FLOW_VERIFICATION), PROVIDER_ZEPTOMAIL)
        self.assertEqual(resolve_provider_for_flow("password_reset"), PROVIDER_DEFAULT)

    @override_settings(ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}))
    def test_unauthorized_flow_cannot_resolve_to_zeptomail(self):
        self.assertEqual(resolve_provider_for_flow("expert_registration"), PROVIDER_DEFAULT)
        self.assertEqual(resolve_provider_for_flow("bureau_approval"), PROVIDER_DEFAULT)


class SendViaProviderTests(SimpleTestCase):
    databases = set()

    @patch("core.email_providers.send_mail", return_value=1)
    def test_default_uses_caller_from_and_django_send_mail(self, mock_send):
        send_via_provider(
            PROVIDER_DEFAULT,
            "Subj",
            "Body",
            "gmail-user@example.test",
            ["to@example.test"],
        )
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        self.assertEqual(args[2], "gmail-user@example.test")
        self.assertNotIn("connection", kwargs)

    @override_settings(
        **_ZEPTO_COMPLETE,
        ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}),
    )
    @patch("core.email_providers.get_connection")
    @patch("core.email_providers.send_mail", return_value=1)
    def test_zeptomail_uses_separate_connection_and_from(self, mock_send, mock_conn):
        conn = MagicMock()
        mock_conn.return_value = conn
        send_via_provider(
            PROVIDER_ZEPTOMAIL,
            "Subj",
            "Body",
            "gmail-user@example.test",  # ignored for ZeptoMail From
            ["to@example.test"],
            flow=FLOW_VERIFICATION,
        )
        mock_conn.assert_called_once()
        conn_kwargs = mock_conn.call_args.kwargs
        self.assertEqual(conn_kwargs["host"], "smtp.zeptomail.in")
        self.assertEqual(conn_kwargs["username"], "emailapikey")
        self.assertEqual(
            conn_kwargs["password"],
            _ZEPTO_COMPLETE["ZEPTOMAIL_EMAIL_HOST_PASSWORD"],
        )
        # EMAIL_* Gmail host must not be used for ZeptoMail connection
        self.assertNotEqual(conn_kwargs["host"], "smtp.gmail.com")
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.args[2], "no-reply@nityadharma.com")
        self.assertIs(mock_send.call_args.kwargs.get("connection"), conn)

    @override_settings(ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}))
    def test_zeptomail_incomplete_fails_closed(self):
        self.assertFalse(zeptomail_settings_complete())
        with self.assertRaises(ImproperlyConfigured):
            send_via_provider(
                PROVIDER_ZEPTOMAIL,
                "Subj",
                "Body",
                "gmail-user@example.test",
                ["to@example.test"],
                flow=FLOW_VERIFICATION,
            )

    @override_settings(
        ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}),
        # Incomplete ZeptoMail on purpose
        ZEPTOMAIL_EMAIL_HOST="smtp.zeptomail.in",
        ZEPTOMAIL_EMAIL_HOST_USER="emailapikey",
        ZEPTOMAIL_EMAIL_HOST_PASSWORD="",
        ZEPTOMAIL_DEFAULT_FROM_EMAIL="no-reply@nityadharma.com",
    )
    @patch("core.email_providers.send_mail", return_value=1)
    def test_allowlisted_but_incomplete_does_not_use_gmail(self, mock_send):
        with self.assertRaises(ImproperlyConfigured):
            send_for_flow(
                FLOW_VERIFICATION,
                "Subj",
                "Body",
                "gmail-user@example.test",
                ["to@example.test"],
            )
        mock_send.assert_not_called()

    @override_settings(**_ZEPTO_COMPLETE, ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}))
    @patch("core.email_providers.send_via_provider", side_effect=RuntimeError("smtp boom"))
    def test_provider_error_does_not_dual_send(self, mock_via):
        with self.assertRaises(RuntimeError):
            send_for_flow(
                FLOW_VERIFICATION,
                "Subj",
                "Body",
                "gmail-user@example.test",
                ["to@example.test"],
            )
        self.assertEqual(mock_via.call_count, 1)


class ProviderAuthorizationHardeningTests(SimpleTestCase):
    """Phase 19: ZeptoMail cannot bypass central flow allowlisting."""

    databases = set()

    @override_settings(
        **_ZEPTO_COMPLETE,
        ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}),
    )
    @patch("core.email_providers.get_connection")
    @patch("core.email_providers.send_mail", return_value=1)
    def test_authorized_flow_can_use_zeptomail(self, mock_send, mock_conn):
        mock_conn.return_value = MagicMock()
        send_via_provider(
            PROVIDER_ZEPTOMAIL,
            "Subj",
            "Body",
            "gmail-user@example.test",
            ["to@example.test"],
            flow=FLOW_VERIFICATION,
        )
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.args[2], "no-reply@nityadharma.com")

    @override_settings(
        **_ZEPTO_COMPLETE,
        ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}),
    )
    @patch("core.email_providers.send_mail", return_value=1)
    def test_unauthorized_flow_cannot_use_zeptomail(self, mock_send):
        with self.assertRaises(ImproperlyConfigured):
            send_via_provider(
                PROVIDER_ZEPTOMAIL,
                "Subj",
                "Body",
                "gmail-user@example.test",
                ["to@example.test"],
                flow="password_reset",
            )
        mock_send.assert_not_called()

    @override_settings(
        **_ZEPTO_COMPLETE,
        ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}),
    )
    @patch("core.email_providers.send_mail", return_value=1)
    def test_missing_flow_cannot_use_zeptomail(self, mock_send):
        with self.assertRaises(ImproperlyConfigured):
            send_via_provider(
                PROVIDER_ZEPTOMAIL,
                "Subj",
                "Body",
                "gmail-user@example.test",
                ["to@example.test"],
            )
        with self.assertRaises(ImproperlyConfigured):
            send_via_provider(
                PROVIDER_ZEPTOMAIL,
                "Subj",
                "Body",
                "gmail-user@example.test",
                ["to@example.test"],
                flow=None,
            )
        mock_send.assert_not_called()

    @override_settings(
        **_ZEPTO_COMPLETE,
        ZEPTOMAIL_ENABLED_FLOWS=frozenset({"verification"}),
    )
    @patch("core.email_providers.send_mail", return_value=1)
    def test_unknown_flow_cannot_bypass_allowlist(self, mock_send):
        with self.assertRaises(ImproperlyConfigured):
            send_via_provider(
                PROVIDER_ZEPTOMAIL,
                "Subj",
                "Body",
                "gmail-user@example.test",
                ["to@example.test"],
                flow="not_a_real_flow",
            )
        mock_send.assert_not_called()

    @patch("core.email_providers.send_mail", return_value=1)
    def test_empty_allowlist_preserves_gmail_default_path(self, mock_send):
        self.assertEqual(resolve_provider_for_flow(FLOW_VERIFICATION), PROVIDER_DEFAULT)
        send_via_provider(
            PROVIDER_DEFAULT,
            "Subj",
            "Body",
            "gmail-user@example.test",
            ["to@example.test"],
            flow=FLOW_VERIFICATION,
        )
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.args[2], "gmail-user@example.test")
        self.assertNotIn("connection", mock_send.call_args.kwargs)
        with self.assertRaises(ImproperlyConfigured):
            send_via_provider(
                PROVIDER_ZEPTOMAIL,
                "Subj",
                "Body",
                "gmail-user@example.test",
                ["to@example.test"],
                flow=FLOW_VERIFICATION,
            )


class QueueOrSendTests(SimpleTestCase):
    databases = set()

    @patch("core.tasks_email.send_email_task.delay")
    def test_queue_passes_flow_kwarg(self, mock_delay):
        result = queue_or_send_transactional_email(
            FLOW_VERIFICATION,
            "Subj",
            "Body",
            "gmail-user@example.test",
            ["to@example.test"],
        )
        self.assertEqual(result, 1)
        mock_delay.assert_called_once()
        self.assertEqual(mock_delay.call_args.kwargs.get("flow"), FLOW_VERIFICATION)

    @patch("core.tasks_email.send_email_task.delay", side_effect=RuntimeError("no broker"))
    @patch("core.email_providers.send_mail", return_value=1)
    def test_sync_fallback_uses_default_when_allowlist_empty(self, mock_send, mock_delay):
        queue_or_send_transactional_email(
            FLOW_VERIFICATION,
            "Subj",
            "Body",
            "gmail-user@example.test",
            ["to@example.test"],
        )
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.args[2], "gmail-user@example.test")
        self.assertNotIn("connection", mock_send.call_args.kwargs)


class TaskBackwardCompatTests(SimpleTestCase):
    databases = set()

    @patch("core.email_providers.send_for_flow")
    def test_task_without_flow_uses_default_resolution(self, mock_send_for_flow):
        from core.tasks_email import send_email_task

        mock_send_for_flow.return_value = 1
        send_email_task.run(
            "Subj",
            "Body",
            "gmail-user@example.test",
            ["to@example.test"],
        )
        mock_send_for_flow.assert_called_once()
        self.assertIsNone(mock_send_for_flow.call_args.args[0])

    def test_resend_env_not_cleared_by_zeptomail_settings_presence(self):
        # Additive settings must not imply changing Resend precedence in prod.py;
        # this settings module keeps RESEND_API_KEY empty and EMAIL_* Gmail-shaped.
        from django.conf import settings as dj_settings

        self.assertEqual(getattr(dj_settings, "RESEND_API_KEY", ""), "")
        self.assertEqual(dj_settings.EMAIL_HOST, "smtp.gmail.com")
        self.assertEqual(dj_settings.ZEPTOMAIL_ENABLED_FLOWS, frozenset())
