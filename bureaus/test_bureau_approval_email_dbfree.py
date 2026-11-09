"""DB-free coverage for bureau approval email (bureaus.signals.trigger_email).

Patches send_mail so no SMTP connection is attempted.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from bureaus.signals import trigger_email

LOCMEM_EMAIL = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(
    EMAIL_BACKEND=LOCMEM_EMAIL,
    EMAIL_HOST="",
    EMAIL_HOST_USER="",
    EMAIL_HOST_PASSWORD="",
    DEFAULT_FROM_EMAIL="noreply@example.test",
)
class BureauApprovalEmailDbFreeTests(SimpleTestCase):
    """Isolate trigger_email recipient/message/from_email=None (Django default From)."""

    databases = set()

    @patch("bureaus.signals.send_mail")
    def test_trigger_email_sends_to_user_with_default_from(self, mock_send_mail):
        profile = SimpleNamespace(
            bureau_name="Test Marriage Bureau",
            user=SimpleNamespace(email="bureau-owner@example.test"),
        )

        trigger_email(profile)

        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args
        # Positional: subject, message, from_email, recipient_list
        subject = kwargs.get("subject", args[0] if args else None)
        message = kwargs.get("message", args[1] if len(args) > 1 else None)
        from_email = kwargs.get("from_email", args[2] if len(args) > 2 else None)
        recipient_list = kwargs.get(
            "recipient_list", args[3] if len(args) > 3 else None
        )
        fail_silently = kwargs.get("fail_silently", None)

        self.assertEqual(subject, "Your Bureau Account is Approved")
        self.assertEqual(recipient_list, ["bureau-owner@example.test"])
        # Existing behavior: from_email is None -> Django uses DEFAULT_FROM_EMAIL.
        self.assertIsNone(from_email)
        self.assertIn("Test Marriage Bureau", message)
        self.assertIn("approved", message.lower())
        self.assertTrue(fail_silently)

    @patch("bureaus.signals.send_mail")
    def test_trigger_email_skips_when_user_email_missing(self, mock_send_mail):
        profile = SimpleNamespace(
            bureau_name="No Email Bureau",
            user=SimpleNamespace(email=""),
        )

        trigger_email(profile)

        mock_send_mail.assert_not_called()
