"""Isolated Broadcast SMS adapter tests. HTTP is mocked; no network call is made."""

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
    SEND_URL,
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


def _assert_exception_hides_secrets(test_case, exc: BaseException, *secrets: str) -> None:
    """Secrets must be absent from the message, chain, and displayed traceback."""

    test_case.assertIsNone(exc.__cause__)
    test_case.assertIsNone(exc.__context__)
    displayed = "".join(traceback.format_exception(exc))
    blob = "\n".join((str(exc), repr(exc), displayed))
    for secret in secrets:
        test_case.assertNotIn(secret, blob)


def _assert_logs_have_no_secrets(test_case, captured) -> None:
    """Check rendered messages and structured record fields."""

    secrets = (_FAKE_API_KEY, _OTP, _DESTINATION, _EXPECTED_NUMBER)
    rendered = "\n".join(captured.output)
    for secret in secrets:
        test_case.assertNotIn(secret, rendered)
    for record in captured.records:
        blob = repr(record.__dict__)
        if record.exc_info:
            blob += repr(record.exc_info)
        for secret in secrets:
            test_case.assertNotIn(secret, blob)
        test_case.assertFalse(hasattr(record, "url"))
        test_case.assertFalse(hasattr(record, "body"))
        test_case.assertNotIn("original", record.__dict__)
        test_case.assertNotIn("normalized", record.__dict__)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


@override_settings(SMS_API_KEY=_FAKE_API_KEY)
class BroadcastSmsProviderIsolationTests(SimpleTestCase):
    databases = set()

    def _provider(self) -> BroadcastSmsProvider:
        provider = BroadcastSmsProvider()
        self.assertEqual(provider.provider_name, constants.PROVIDER_BROADCAST_SMS)
        self.assertEqual(provider.provider_name, "broadcast_sms")
        return provider

    def _assert_outbound(self, get_mock: MagicMock) -> dict:
        self.assertEqual(get_mock.call_count, 1)
        args, kwargs = get_mock.call_args
        self.assertEqual(args[0], SEND_URL)
        self.assertIn("dashboard.broadcast.run", args[0])
        params = kwargs["params"]
        self.assertEqual(params["Number"], _EXPECTED_NUMBER)
        self.assertEqual(params["SenderId"], "NDHRMA")
        self.assertEqual(params["PeId"], "1701177338710464858")
        self.assertEqual(params["DLTTemplateId"], "1777178575487318004")
        self.assertEqual(params["Text"], _OTP_SMS_TEMPLATE.format(otp=_OTP))
        self.assertIn(_OTP, params["Text"])
        self.assertNotIn("{otp}", params["Text"])
        _assert_secret_not_leaked("ApiKey parameter", params["ApiKey"])
        _assert_secret_not_leaked(
            "Authorization header",
            kwargs["headers"]["Authorization"].removeprefix("Bearer "),
        )
        self.assertTrue(kwargs["headers"]["Authorization"].startswith("Bearer "))
        self.assertEqual(kwargs["timeout"], 10)
        return params

    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_success_response_is_accepted_without_network(self, get_mock):
        payload = {
            "code": "200",
            "message": json.dumps([{"messageId": "msg-isolated-1"}]),
        }
        get_mock.return_value = _FakeResponse(
            200,
            payload,
            text='{"code":"200","echo":"' + _OTP + '","number":"' + _EXPECTED_NUMBER + '"}',
        )

        with self.assertLogs(
            "otp_verification.providers.broadcast_sms",
            level="INFO",
        ) as captured:
            result = self._provider().send(_request())

        self._assert_outbound(get_mock)
        self.assertTrue(result.accepted)
        self.assertEqual(result.provider_name, "broadcast_sms")
        self.assertEqual(result.provider_reference, "msg-isolated-1")
        _assert_logs_have_no_secrets(self, captured)
        self.assertTrue(
            any(getattr(record, "http_status", None) == 200 for record in captured.records)
        )

    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_timeout_maps_to_provider_timeout(self, get_mock):
        leaked_url = (
            SEND_URL
            + "?ApiKey="
            + _FAKE_API_KEY
            + "&Text="
            + _OTP
            + "&Number="
            + _EXPECTED_NUMBER
        )
        get_mock.side_effect = requests.Timeout(leaked_url)
        with self.assertLogs(
            "otp_verification.providers.broadcast_sms",
            level="INFO",
        ) as captured:
            with self.assertRaises(ProviderTimeoutException) as raised:
                self._provider().send(_request())
        self.assertEqual(str(raised.exception), "broadcast_sms request timed out.")
        _assert_exception_hides_secrets(
            self,
            raised.exception,
            leaked_url,
            _FAKE_API_KEY,
            _OTP,
            _EXPECTED_NUMBER,
        )
        self._assert_outbound(get_mock)
        _assert_logs_have_no_secrets(self, captured)
        self.assertNotIn(leaked_url, "\n".join(captured.output))
        for record in captured.records:
            self.assertNotIn(leaked_url, repr(record.__dict__))

    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_connection_failure_maps_to_provider_unavailable(self, get_mock):
        leaked_url = (
            SEND_URL
            + "?ApiKey="
            + _FAKE_API_KEY
            + "&Text="
            + _OTP
            + "&Number="
            + _DESTINATION
        )
        get_mock.side_effect = requests.ConnectionError(leaked_url)
        with self.assertLogs(
            "otp_verification.providers.broadcast_sms",
            level="INFO",
        ) as captured:
            with self.assertRaises(ProviderUnavailableException) as raised:
                self._provider().send(_request())
        self.assertEqual(str(raised.exception), "broadcast_sms provider unavailable.")
        _assert_exception_hides_secrets(
            self,
            raised.exception,
            leaked_url,
            _FAKE_API_KEY,
            _OTP,
            _DESTINATION,
            _EXPECTED_NUMBER,
        )
        self._assert_outbound(get_mock)
        _assert_logs_have_no_secrets(self, captured)
        for record in captured.records:
            self.assertNotIn(leaked_url, repr(record.__dict__))

    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_http_failure_maps_to_provider_failure(self, get_mock):
        sensitive_body = "upstream " + _OTP + " " + _EXPECTED_NUMBER + " " + _FAKE_API_KEY
        get_mock.return_value = _FakeResponse(503, text=sensitive_body)
        with self.assertLogs(
            "otp_verification.providers.broadcast_sms",
            level="INFO",
        ) as captured:
            with self.assertRaises(ProviderFailureException) as raised:
                self._provider().send(_request())
        self.assertEqual(
            str(raised.exception),
            "broadcast_sms delivery failed with HTTP 503.",
        )
        _assert_exception_hides_secrets(
            self,
            raised.exception,
            sensitive_body,
            _OTP,
            _EXPECTED_NUMBER,
            _FAKE_API_KEY,
        )
        self._assert_outbound(get_mock)
        _assert_logs_have_no_secrets(self, captured)

    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_unsuccessful_api_code_maps_to_provider_failure(self, get_mock):
        provider_message = "rejected " + _OTP + " " + _EXPECTED_NUMBER + " " + _FAKE_API_KEY
        get_mock.return_value = _FakeResponse(
            200,
            {"code": "400", "message": provider_message},
            text='{"code":"400","message":"' + provider_message + '"}',
        )
        with self.assertRaises(ProviderFailureException) as raised:
            self._provider().send(_request())
        self.assertEqual(
            str(raised.exception),
            "broadcast_sms delivery failed with a non-success API code.",
        )
        _assert_exception_hides_secrets(
            self,
            raised.exception,
            provider_message,
            _OTP,
            _EXPECTED_NUMBER,
            _FAKE_API_KEY,
            "rejected",
        )
        self._assert_outbound(get_mock)

    @override_settings(SMS_API_KEY="")
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_empty_sms_api_key_raises_configuration_exception_without_http(self, get_mock):
        previous = os.environ.pop("SMS_API_KEY", None)
        try:
            with self.assertNoLogs(
                "otp_verification.providers.broadcast_sms",
                level="INFO",
            ):
                with self.assertRaises(ConfigurationException) as raised:
                    self._provider().send(_request())
        finally:
            if previous is not None:
                os.environ["SMS_API_KEY"] = previous
        self.assertEqual(
            str(raised.exception),
            "SMS_API_KEY is required for broadcast_sms provider.",
        )
        get_mock.assert_not_called()

    @override_settings(SMS_API_KEY=None)
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_absent_sms_api_key_raises_configuration_exception_without_http(self, get_mock):
        previous = os.environ.pop("SMS_API_KEY", None)
        try:
            with self.assertNoLogs(
                "otp_verification.providers.broadcast_sms",
                level="INFO",
            ):
                with self.assertRaises(ConfigurationException) as raised:
                    self._provider().send(_request())
        finally:
            if previous is not None:
                os.environ["SMS_API_KEY"] = previous
        self.assertEqual(
            str(raised.exception),
            "SMS_API_KEY is required for broadcast_sms provider.",
        )
        get_mock.assert_not_called()

    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_json_null_response_maps_to_provider_failure(self, get_mock):
        response = _FakeResponse(200)
        response.json = MagicMock(return_value=None)
        get_mock.return_value = response
        with self.assertRaises(ProviderFailureException) as raised:
            self._provider().send(_request())
        self.assertEqual(
            str(raised.exception),
            "broadcast_sms returned an unexpected response format.",
        )
        self._assert_outbound(get_mock)
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_json_list_response_maps_to_provider_failure(self, get_mock):
        response = _FakeResponse(200)
        response.json = MagicMock(return_value=[])
        get_mock.return_value = response
        with self.assertRaises(ProviderFailureException) as raised:
            self._provider().send(_request())
        self.assertEqual(
            str(raised.exception),
            "broadcast_sms returned an unexpected response format.",
        )
        self._assert_outbound(get_mock)
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_json_string_response_maps_to_provider_failure(self, get_mock):
        response = _FakeResponse(200)
        response.json = MagicMock(return_value="unexpected")
        get_mock.return_value = response
        with self.assertRaises(ProviderFailureException) as raised:
            self._provider().send(_request())
        self.assertEqual(
            str(raised.exception),
            "broadcast_sms returned an unexpected response format.",
        )
        self._assert_outbound(get_mock)
    @patch("otp_verification.providers.broadcast_sms.requests.get")
    def test_non_json_response_maps_to_provider_failure(self, get_mock):
        secret_body = "upstream-body " + _OTP + " " + _EXPECTED_NUMBER + " " + _FAKE_API_KEY
        response = _FakeResponse(200, text=secret_body)
        response.json = MagicMock(side_effect=ValueError("not json " + secret_body))
        get_mock.return_value = response
        with self.assertLogs(
            "otp_verification.providers.broadcast_sms",
            level="INFO",
        ) as captured:
            with self.assertRaises(ProviderFailureException) as raised:
                self._provider().send(_request())
        self.assertEqual(
            str(raised.exception),
            "broadcast_sms returned a non-JSON response.",
        )
        _assert_exception_hides_secrets(
            self,
            raised.exception,
            secret_body,
            _FAKE_API_KEY,
            _OTP,
            _EXPECTED_NUMBER,
            "not json",
        )
        self._assert_outbound(get_mock)
        _assert_logs_have_no_secrets(self, captured)
        rendered = "\n".join(captured.output)
        self.assertNotIn(secret_body, rendered)
        for record in captured.records:
            self.assertNotIn(secret_body, repr(record.__dict__))
