"""DB-free coverage for bureau approval email (bureaus.signals.trigger_email).

Patches queue_or_send_transactional_email so no SMTP/Celery/broker is used.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from bureaus.signals import (
    _is_bureau_email_eligible,
    send_email_on_approval,
    trigger_email,
)
from core.email_providers import FLOW_BUREAU_APPROVAL

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

    @patch("bureaus.signals.queue_or_send_transactional_email")
    def test_trigger_email_sends_to_user_with_default_from(self, mock_queue):
        profile = SimpleNamespace(
            bureau_name="Test Marriage Bureau",
            user=SimpleNamespace(email="bureau-owner@example.test"),
        )

        trigger_email(profile)

        mock_queue.assert_called_once()
        args, kwargs = mock_queue.call_args
        self.assertEqual(args[0], FLOW_BUREAU_APPROVAL)
        self.assertEqual(args[1], "Your Bureau Account is Approved")
        self.assertIn("Test Marriage Bureau", args[2])
        self.assertIn("approved", args[2].lower())
        self.assertIsNone(args[3])
        self.assertEqual(args[4], ["bureau-owner@example.test"])
        self.assertTrue(kwargs.get("fail_silently"))

    @patch("bureaus.signals.queue_or_send_transactional_email")
    def test_trigger_email_skips_when_user_email_missing(self, mock_queue):
        profile = SimpleNamespace(
            bureau_name="No Email Bureau",
            user=SimpleNamespace(email=""),
        )

        trigger_email(profile)

        mock_queue.assert_not_called()

    @patch("bureaus.signals.trigger_email")
    def test_eligibility_transition_sends_once(self, mock_trigger):
        profile = SimpleNamespace(
            is_approved=True,
            is_active=True,
            is_email_verified=True,
            _previous_is_eligible=False,
        )
        self.assertTrue(_is_bureau_email_eligible(profile))
        send_email_on_approval(sender=None, instance=profile, created=False)
        mock_trigger.assert_called_once_with(profile)

    @patch("bureaus.signals.trigger_email")
    def test_already_eligible_save_does_not_resend(self, mock_trigger):
        profile = SimpleNamespace(
            is_approved=True,
            is_active=True,
            is_email_verified=True,
            _previous_is_eligible=True,
        )
        send_email_on_approval(sender=None, instance=profile, created=False)
        mock_trigger.assert_not_called()

    @patch("bureaus.signals.trigger_email")
    def test_created_profile_does_not_send(self, mock_trigger):
        profile = SimpleNamespace(
            is_approved=True,
            is_active=True,
            is_email_verified=True,
            _previous_is_eligible=False,
        )
        send_email_on_approval(sender=None, instance=profile, created=True)
        mock_trigger.assert_not_called()
