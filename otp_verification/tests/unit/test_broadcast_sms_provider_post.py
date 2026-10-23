"""Isolated POST adapter tests. All HTTP is mocked; no network calls are made."""

import json
import os
import traceback
from unittest.mock import patch

import requests
from django.test import SimpleTestCase, override_settings

from otp_verification.exceptions import (
    ConfigurationException,
    ProviderFailureException,
    ProviderTimeoutException,
    ProviderUnavailableException,
)
from otp_verification.interfaces.providers import ProviderRequest
from otp_verification.providers.broadcast_sms import (
    CHAIN_VALUE,
    DLT_TEMPLATE_ID,
    PE_ID,
    POST_SEND_URL,
    SENDER_ID,
    TIMEOUT_SECONDS,
    BroadcastSmsProvider,
)

FAKE_KEY = "TEST_POST_BROADCAST_KEY"
OTP = "482913"
DESTINATION = "9876543210"
NORMALIZED = "919876543210"


class FakeResponse:
    def __init__(self, status_code, payload=None, json_error=None):
        self.status_code = status_code
        self.payload = payload
        self.json_error = json_error

    def json(self):
        if self.json_error:
            raise ValueError("private fake response detail " + FAKE_KEY + OTP)
        return self.payload


def request():
    return ProviderRequest(
        destination=DESTINATION,
        message=OTP,
        channel="sms",
        metadata={"challenge_id": "isolated-post-test"},
    )


def observed_success():
    return {
        "code": "200",
        "message": json.dumps([{"messageId": "mock-message-001"}]),
    }


@override_settings(SMS_API_KEY=FAKE_KEY, BROADCAST_SMS_TRANSPORT="post")
class BroadcastSmsPostDraftTests(SimpleTestCase):
    databases = set()

    def assert_safe_error(self, exc):
        self.assertIsNone(exc.__cause__)
        self.assertIsNone(exc.__context__)
        rendered = "".join(traceback.format_exception(exc))
        for secret in (FAKE_KEY, OTP, DESTINATION, NORMALIZED):
            self.assertNotIn(secret, str(exc))
            self.assertNotIn(secret, rendered)

    def assert_post_request(self, mock_post):
        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args
        self.assertEqual(args, (POST_SEND_URL,))
        self.assertEqual(
            POST_SEND_URL, "https://dashboard.broadcast.run/api/v1/send"
        )
        self.assertEqual(
            kwargs["headers"],
            {
                "Authorization": "Bearer " + FAKE_KEY,
                "Content-Type": "application/json",
            },
        )
        self.assertEqual(kwargs["timeout"], TIMEOUT_SECONDS)
        self.assertNotIn(FAKE_KEY, repr(kwargs["json"]))
        self.assertNotIn(OTP, kwargs["json"]["content"]["data"]["text"])

        body = kwargs["json"]
        self.assertEqual(body["channel"], "SMS")
        self.assertEqual(body["to"], [NORMALIZED])
        self.assertEqual(body["from"], SENDER_ID)
        data = body["content"]["data"]
        self.assertEqual(data["dlttemplateid"], DLT_TEMPLATE_ID)
        self.assertEqual(data["peid"], PE_ID)
        self.assertEqual(data["chainvalue"], CHAIN_VALUE)
        self.assertIn("{#var1#}", data["text"])
        self.assertEqual(body["content"]["params"], {"var1": OTP})

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_post_success_uses_documented_json_and_parses_observed_response(self, mock_post):
        mock_post.return_value = FakeResponse(200, observed_success())
        result = BroadcastSmsProvider().send(request())
        self.assert_post_request(mock_post)
        self.assertTrue(result.accepted)
        self.assertEqual(result.provider_reference, "mock-message-001")
        self.assertEqual(result.provider_name, "broadcast_sms")

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_timeout_is_safe_and_does_not_retry(self, mock_post):
        mock_post.side_effect = requests.Timeout(
            "private URL " + FAKE_KEY + " " + OTP + " " + DESTINATION
        )
        with self.assertRaises(ProviderTimeoutException) as caught:
            BroadcastSmsProvider().send(request())
        self.assertEqual(str(caught.exception), "broadcast_sms request timed out.")
        self.assert_safe_error(caught.exception)
        self.assertEqual(mock_post.call_count, 1)

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_connection_error_is_safe_and_does_not_retry(self, mock_post):
        mock_post.side_effect = requests.ConnectionError(
            "private URL " + FAKE_KEY + " " + OTP + " " + DESTINATION
        )
        with self.assertRaises(ProviderUnavailableException) as caught:
            BroadcastSmsProvider().send(request())
        self.assertEqual(str(caught.exception), "broadcast_sms provider unavailable.")
        self.assert_safe_error(caught.exception)
        self.assertEqual(mock_post.call_count, 1)

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_http_failure_does_not_expose_response_body(self, mock_post):
        mock_post.return_value = FakeResponse(503, {"private": FAKE_KEY + OTP})
        with self.assertRaises(ProviderFailureException) as caught:
            BroadcastSmsProvider().send(request())
        self.assertEqual(str(caught.exception), "broadcast_sms delivery failed with HTTP 503.")
        self.assert_safe_error(caught.exception)
        self.assertEqual(mock_post.call_count, 1)

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_non_success_api_code_is_rejected(self, mock_post):
        mock_post.return_value = FakeResponse(
            200, {"code": "400", "message": "rejected"}
        )
        with self.assertRaises(ProviderFailureException):
            BroadcastSmsProvider().send(request())

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_unconfirmed_response_shapes_are_rejected(self, mock_post):
        generic = "broadcast_sms success response missing provider messageId."
        cases = (
            ("none", None, ()),
            ("empty_list_payload", [], ()),
            ("string_payload", "unexpected", ()),
            ("message_already_a_list", {"code": "200", "message": [{"messageId": "not-confirmed"}]}, ()),
            ("message_not_json", {"code": "200", "message": "not-json"}, ()),
            ("empty_message_list", {"code": "200", "message": "[]"}, ()),
            ("empty_message_id", {"code": "200", "message": '[{"messageId": ""}]'}, ()),
            ("first_entry_null", {"code": "200", "message": "[null]"}, ("[null]", "null")),
            ("first_entry_string", {"code": "200", "message": '["unexpected"]'}, ('["unexpected"]', "unexpected")),
            ("first_entry_number", {"code": "200", "message": "[123]"}, ("[123]", "123")),
        )
        for label, payload, forbidden in cases:
            with self.subTest(case=label):
                mock_post.return_value = FakeResponse(200, payload)
                with self.assertRaises(ProviderFailureException) as caught:
                    BroadcastSmsProvider().send(request())
                if forbidden:
                    self.assertEqual(str(caught.exception), generic)
                    self.assert_safe_error(caught.exception)
                    rendered = "".join(traceback.format_exception(caught.exception))
                    for fragment in forbidden:
                        self.assertNotIn(fragment, str(caught.exception))
                        self.assertNotIn(fragment, rendered)

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_non_json_response_error_hides_secrets(self, mock_post):
        mock_post.return_value = FakeResponse(
            200, json_error=True
        )
        with self.assertRaises(ProviderFailureException) as caught:
            BroadcastSmsProvider().send(request())
        self.assert_safe_error(caught.exception)

    @override_settings(SMS_API_KEY="", BROADCAST_SMS_TRANSPORT="post")
    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_missing_api_key_does_not_make_http_request(self, mock_post):
        previous = os.environ.pop("SMS_API_KEY", None)
        try:
            with self.assertRaises(ConfigurationException):
                BroadcastSmsProvider().send(request())
        finally:
            if previous is not None:
                os.environ["SMS_API_KEY"] = previous
        mock_post.assert_not_called()


@override_settings(SMS_API_KEY=FAKE_KEY)
class BroadcastSmsTransportSelectionTests(SimpleTestCase):
    databases = set()

    def _req(self):
        return request()

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_missing_transport_defaults_to_get(self, mock_get, mock_post):
        mock_get.return_value = FakeResponse(200, observed_success())
        previous = os.environ.pop("BROADCAST_SMS_TRANSPORT", None)
        try:
            result = BroadcastSmsProvider().send(self._req())
        finally:
            if previous is not None:
                os.environ["BROADCAST_SMS_TRANSPORT"] = previous
        self.assertTrue(result.accepted)
        self.assertEqual(mock_get.call_count, 1)
        mock_post.assert_not_called()
        self.assertEqual(
            mock_get.call_args[0][0],
            "https://dashboard.broadcast.run/api/v1/sms/sendsms",
        )

    @override_settings(SMS_API_KEY=FAKE_KEY, BROADCAST_SMS_TRANSPORT="get")
    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_explicit_get_uses_existing_get_endpoint(self, mock_get, mock_post):
        mock_get.return_value = FakeResponse(200, observed_success())
        result = BroadcastSmsProvider().send(self._req())
        self.assertTrue(result.accepted)
        self.assertEqual(mock_get.call_count, 1)
        mock_post.assert_not_called()
        self.assertEqual(mock_get.call_args[0][0], "https://dashboard.broadcast.run/api/v1/sms/sendsms")

    @override_settings(SMS_API_KEY=FAKE_KEY, BROADCAST_SMS_TRANSPORT="post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_explicit_post_uses_post_endpoint_and_json_schema(self, mock_post, mock_get):
        mock_post.return_value = FakeResponse(200, observed_success())
        result = BroadcastSmsProvider().send(self._req())
        self.assertTrue(result.accepted)
        self.assertEqual(mock_post.call_count, 1)
        mock_get.assert_not_called()
        args, kwargs = mock_post.call_args
        self.assertEqual(args, (POST_SEND_URL,))
        body = kwargs["json"]
        self.assertEqual(body["channel"], "SMS")
        self.assertEqual(body["to"], [NORMALIZED])
        self.assertEqual(body["from"], SENDER_ID)
        self.assertEqual(body["content"]["data"]["dlttemplateid"], DLT_TEMPLATE_ID)
        self.assertEqual(body["content"]["data"]["peid"], PE_ID)
        self.assertEqual(body["content"]["data"]["chainvalue"], CHAIN_VALUE)
        self.assertIn("{#var1#}", body["content"]["data"]["text"])
        self.assertEqual(body["content"]["params"], {"var1": OTP})

    @override_settings(SMS_API_KEY=FAKE_KEY, BROADCAST_SMS_TRANSPORT="ftp")
    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_invalid_transport_fails_before_http(self, mock_get, mock_post):
        with self.assertRaises(ConfigurationException):
            BroadcastSmsProvider().send(self._req())
        mock_get.assert_not_called()
        mock_post.assert_not_called()
