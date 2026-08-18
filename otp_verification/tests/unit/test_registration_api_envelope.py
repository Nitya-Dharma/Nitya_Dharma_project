"""Additive API envelope contract for registration OTP JSON helpers."""

from __future__ import annotations

import json
from django.test import SimpleTestCase

from otp_verification.registration.responses import (
    ERROR_COOLDOWN,
    send_success_json,
    verification_error_json,
    verification_success_json,
)


def _body(response):
    return json.loads(response.content.decode("utf-8"))


class AdditiveApiEnvelopeTests(SimpleTestCase):
    def test_send_success_keeps_flat_fields_and_adds_result(self):
        response = send_success_json(
            message="Verification code sent.",
            challenge_id="chal-1",
            flow_type="user_registration",
            expires_at="2026-01-01T00:00:00+00:00",
            cooldown_remaining=60,
        )
        body = _body(response)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["challenge_id"], "chal-1")
        self.assertEqual(body["cooldown_remaining"], 60)
        self.assertIsNone(body["error_code"])
        self.assertEqual(body["result"]["challenge_id"], "chal-1")
        self.assertEqual(body["result"]["cooldown_remaining"], 60)
        self.assertEqual(body["result"]["flow_type"], "user_registration")
        self.assertIn("message", body)

    def test_verify_success_adds_error_code_null(self):
        response = verification_success_json(
            message="Phone number verified.",
            result={"phone_verified": True, "challenge_id": "c1"},
        )
        body = _body(response)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["result"]["phone_verified"], True)
        self.assertIsNone(body["error_code"])
        self.assertIn("message", body)

    def test_error_keeps_error_and_adds_error_code_and_null_result(self):
        response = verification_error_json(
            error=ERROR_COOLDOWN,
            message="Please wait before requesting a new OTP.",
            status=429,
            remaining_seconds=12,
        )
        body = _body(response)
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["error"], ERROR_COOLDOWN)
        self.assertEqual(body["error_code"], ERROR_COOLDOWN)
        self.assertIsNone(body["result"])
        self.assertEqual(body["remaining_seconds"], 12)
        self.assertIn("message", body)
