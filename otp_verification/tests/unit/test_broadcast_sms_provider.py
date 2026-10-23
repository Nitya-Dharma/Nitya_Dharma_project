"""Isolated Broadcast SMS GET adapter tests. HTTP is mocked; no network call is made."""

from __future__ import annotations

import json
import os
import traceback
from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.exceptions import (
    ConfigurationException,
    ProviderFailureException,
    ProviderTimeoutException,
    ProviderUnavailableException,
)
from otp_verification.interfaces.providers import ProviderRequest
from otp_verification.providers.broadcast_sms import (
    DLT_TEMPLATE_ID,
    PE_ID,
    SEND_URL,
    SENDER_ID,
    TIMEOUT_SECONDS,
    BroadcastSmsProvider,
    _OTP_SMS_TEMPLATE,
)

_FAKE_API_KEY = "TEST_BROADCAST_API_KEY"
_OTP = "482913"
_DESTINATION = "9876543210"
_EXPECTED_NUMBER = "919876543210"


def _request() -> ProviderRequest:
    return ProviderRequest(
        destination=_DESTINATION,
        message=_OTP,
        channel="sms",
        metadata={"challenge_id": "isolated-test"},
    )


def _assert_secret_not_leaked(label: str, actual: str) -> None:
    if actual != _FAKE_API_KEY:
        raise AssertionError(label + " did not match the isolated test credential")


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("private fake response detail " + _FAKE_API_KEY + _OTP)
        return self._payload


@override_settings(SMS_API_KEY=_FAKE_API_KEY)
class BroadcastSmsProviderIsolationTests(SimpleTestCase):
    databases = set()

    def assert_safe_error(self, exc):
        self.assertIsNone(exc.__cause__)
        self.assertIsNone(exc.__context__)
        rendered = "".join(traceback.format_exception(exc))
        for secret in (_FAKE_API_KEY, _OTP, _DESTINATION, _EXPECTED_NUMBER):
            self.assertNotIn(secret, str(exc))
            self.assertNotIn(secret, rendered)

    def _provider(self) -> BroadcastSmsProvider:
        provider = BroadcastSmsProvider()
        self.assertEqual(provider.provider_name, constants.PROVIDER_BROADCAST_SMS)
        self.assertEqual(provider.provider_name, "broadcast_sms")
        return provider

    def _assert_outbound(self, get_mock: MagicMock) -> dict:
        self.assertEqual(get_mock.call_count, 1)
        args, kwargs = get_mock.call_args
        self.assertEqual(args[0], SEND_URL)
        self.assertEqual(SEND_URL, "https://dashboard.broadcast.run/api/v1/sms/sendsms")
        self.assertIn("dashboard.broadcast.run", args[0])
        params = kwargs["params"]
        self.assertEqual(params["Number"], _EXPECTED_NUMBER)
        self.assertEqual(params["SenderId"], SENDER_ID)
        self.assertEqual(params["PeId"], PE_ID)
        self.assertEqual(params["DLTTemplateId"], DLT_TEMPLATE_ID)
        self.assertEqual(params["Text"], _OTP_SMS_TEMPLATE.format(otp=_OTP))
        self.assertIn(_OTP, params["Text"])
        self.assertNotIn("{otp}", params["Text"])
        self.assertNotIn("{#var1#}", params["Text"])
        _assert_secret_not_leaked("ApiKey parameter", params["ApiKey"])
        _assert_secret_not_leaked(
            "Authorization header",
            kwargs["headers"]["Authorization"].removeprefix("Bearer "),
        )
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Bearer "))
        self.assertEqual(kwargs["timeout"], TIMEOUT_SECONDS)
        return params

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_success_response_is_accepted_without_network(self, get_mock, post_mock):
        payload = {
            "code": "200",
            "message": json.dumps([{"messageId": "msg-isolated-1"}]),
        }
        get_mock.return_value = _FakeResponse(200, payload, text='{"code":"200"}')

        with self.assertLogs(
            "otp_verification.providers.broadcast_sms",
            level="INFO",
        ) as captured:
            result = self._provider().send(_request())

        self._assert_outbound(get_mock)
        post_mock.assert_not_called()
        self.assertTrue(result.accepted)
        self.assertEqual(result.provider_name, "broadcast_sms")
        self.assertEqual(result.provider_reference, "msg-isolated-1")
        rendered_logs = "\n".join(captured.output)
        self.assertNotIn(_FAKE_API_KEY, rendered_logs)
        self.assertNotIn(_OTP, rendered_logs)

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_timeout_is_safe_and_does_not_retry(self, get_mock, post_mock):
        get_mock.side_effect = requests.Timeout(
            "private URL " + _FAKE_API_KEY + " " + _OTP + " " + _DESTINATION
        )
        with self.assertRaises(ProviderTimeoutException) as caught:
            self._provider().send(_request())
        self.assertEqual(str(caught.exception), "broadcast_sms request timed out.")
        self.assert_safe_error(caught.exception)
        self.assertEqual(get_mock.call_count, 1)
        post_mock.assert_not_called()

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_connection_error_is_safe_and_does_not_retry(self, get_mock, post_mock):
        get_mock.side_effect = requests.ConnectionError(
            "private URL " + _FAKE_API_KEY + " " + _OTP + " " + _DESTINATION
        )
        with self.assertRaises(ProviderUnavailableException) as caught:
            self._provider().send(_request())
        self.assertEqual(str(caught.exception), "broadcast_sms provider unavailable.")
        self.assert_safe_error(caught.exception)
        self.assertEqual(get_mock.call_count, 1)
        post_mock.assert_not_called()

    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_http_failure_does_not_expose_response_body(self, get_mock, post_mock):
        get_mock.return_value = _FakeResponse(503, {"private": _FAKE_API_KEY + _OTP})
        with self.assertRaises(ProviderFailureException) as caught:
            self._provider().send(_request())
        self.assertEqual(
            str(caught.exception), "broadcast_sms delivery failed with HTTP 503."
        )
        self.assert_safe_error(caught.exception)
        self.assertEqual(get_mock.call_count, 1)
        post_mock.assert_not_called()

    @override_settings(SMS_API_KEY=_FAKE_API_KEY, BROADCAST_SMS_TRANSPORT="get")
    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_non_success_api_code_is_rejected(self, get_mock, post_mock):
        get_mock.return_value = _FakeResponse(
            200, {"code": "400", "message": "rejected"}
        )
        with self.assertRaises(ProviderFailureException) as caught:
            self._provider().send(_request())
        self.assertEqual(
            str(caught.exception),
            "broadcast_sms delivery failed with a non-success API code.",
        )
        self.assert_safe_error(caught.exception)
        post_mock.assert_not_called()

    @override_settings(SMS_API_KEY=_FAKE_API_KEY, BROADCAST_SMS_TRANSPORT="get")
    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_malformed_responses_are_rejected(self, get_mock, post_mock):
        for payload in (
            [],
            "unexpected",
            {"code": "200", "message": [{"messageId": "not-confirmed"}]},
            {"code": "200", "message": "not-json"},
            {"code": "200", "message": "[]"},
            {"code": "200", "message": '[{"messageId": ""}]'},
        ):
            with self.subTest(payload=payload):
                get_mock.return_value = _FakeResponse(200, payload)
                with self.assertRaises(ProviderFailureException):
                    self._provider().send(_request())
                post_mock.assert_not_called()

    @override_settings(SMS_API_KEY=_FAKE_API_KEY, BROADCAST_SMS_TRANSPORT="get")
    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_malformed_first_list_entries_raise_generic_failure(self, get_mock, post_mock):
        generic = "broadcast_sms success response missing provider messageId."
        cases = (
            ("null_entry", "[null]", ("[null]", "null")),
            ("string_entry", '["unexpected"]', ('["unexpected"]', "unexpected")),
            ("numeric_entry", "[123]", ("[123]", "123")),
        )
        for label, message, forbidden in cases:
            with self.subTest(case=label):
                get_mock.return_value = _FakeResponse(
                    200, {"code": "200", "message": message}
                )
                with self.assertRaises(ProviderFailureException) as caught:
                    self._provider().send(_request())
                self.assertEqual(str(caught.exception), generic)
                self.assert_safe_error(caught.exception)
                rendered = "".join(traceback.format_exception(caught.exception))
                for fragment in forbidden:
                    self.assertNotIn(fragment, str(caught.exception))
                    self.assertNotIn(fragment, rendered)
                post_mock.assert_not_called()

    @override_settings(SMS_API_KEY=_FAKE_API_KEY, BROADCAST_SMS_TRANSPORT="get")
    @patch("otp_verification.providers.broadcast_sms.requests.post")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_non_json_response_error_hides_secrets(self, get_mock, post_mock):
        get_mock.return_value = _FakeResponse(200, payload=None)
        with self.assertRaises(ProviderFailureException) as caught:
            self._provider().send(_request())
        self.assertEqual(
            str(caught.exception), "broadcast_sms returned a non-JSON response."
        )
        self.assert_safe_error(caught.exception)
        post_mock.assert_not_called()

    @override_settings(SMS_API_KEY="")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    @patch("otp_verification.providers.broadcast_sms.requests.post")
    def test_missing_api_key_does_not_make_http_request(self, post_mock, get_mock):
        previous = os.environ.pop("SMS_API_KEY", None)
        try:
            with self.assertRaises(ConfigurationException):
                self._provider().send(_request())
        finally:
            if previous is not None:
                os.environ["SMS_API_KEY"] = previous
        get_mock.assert_not_called()
        post_mock.assert_not_called()
