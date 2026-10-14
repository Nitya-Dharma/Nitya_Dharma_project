"""Log-record checks for phone normalization. No database and no network."""

from __future__ import annotations

from django.test import SimpleTestCase

from otp_verification.registration.adapters import normalize_destination

_PHONE = "9876543210"
_NORMALIZED = "919876543210"


class PhoneNormalizationLogTests(SimpleTestCase):
    databases = set()

    def test_normalized_phone_is_not_passed_to_the_logger(self):
        with self.assertLogs(
            "otp_verification.registration.adapters",
            level="INFO",
        ) as captured:
            result = normalize_destination(_PHONE)

        self.assertEqual(result, _NORMALIZED)
        rendered = "\n".join(captured.output)
        self.assertNotIn(_PHONE, rendered)
        self.assertNotIn(_NORMALIZED, rendered)
        for record in captured.records:
            blob = repr(record.__dict__)
            self.assertNotIn(_PHONE, blob)
            self.assertNotIn(_NORMALIZED, blob)
            self.assertNotIn("original", record.__dict__)
            self.assertNotIn("normalized", record.__dict__)
