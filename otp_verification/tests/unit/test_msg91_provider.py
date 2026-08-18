"""Unit/integration tests for MSG91 SMS provider and HTTP transport."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration, validate_msg91_configuration
from otp_verification.enums import DeliveryChannel, ProviderResultStatus, SimulationMode
from otp_verification.exceptions import (
    ConfigurationException,
    InvalidPhoneException,
    InvalidProviderResponseException,
    ProviderAuthenticationException,
    ProviderFailureException,
    ProviderTimeoutException,
    ProviderUnavailableException,
    SecurityException,
)
from otp_verification.interfaces.providers import ProviderRequest
from otp_verification.providers.msg91 import Msg91SmsProvider
from otp_verification.providers.mock import MockOTPProvider
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.security.contracts import ReplayProtection
from otp_verification.storage.memory import InMemoryChallengeRepository
from otp_verification.services.support import AuditLogger
from otp_verification.logging.contracts import AuditEventPayload, LoggingBackend
from otp_verification.transport.exceptions import (
    TransportAuthenticationError,
    TransportTimeoutError,
    TransportUnavailableError,
)
from otp_verification.transport.http import HttpTransportResult, RequestsHttpTransport


class CaptureBackend(LoggingBackend):
    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit(self, payload: AuditEventPayload) -> None:
        self.events.append({"event": payload.event, "metadata": dict(payload.metadata)})


def _msg91_config(**overrides) -> OTPConfiguration:
    base = dict(
        enabled=True,
        mode="real",
        provider=constants.PROVIDER_MSG91,
        enabled_flows=("user_registration",),
        otp_expiry_seconds=600,
        resend_cooldown_seconds=30,
        otp_length=6,
        max_attempts=3,
        max_resends=3,
        provider_enabled=True,
        mock_simulation_mode=SimulationMode.SUCCESS,
        mock_execution_delay_ms=0,
        mock_allow_random=False,
        provider_audit_enabled=True,
        provider_metrics_enabled=True,
        msg91_auth_key="test-auth-key",
        msg91_base_url="https://control.msg91.com/api/v5/flow/",
        msg91_flow_id="flow-123",
        msg91_sender_id="NITYAD",
        msg91_template_variable="OTP",
        msg91_country_code="91",
        msg91_timeout_seconds=10,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


def _mock_config(**overrides) -> OTPConfiguration:
    base = dict(
        enabled=True,
        mode="mock",
        provider=constants.PROVIDER_MOCK_SMS,
        enabled_flows=("user_registration",),
        otp_expiry_seconds=600,
        resend_cooldown_seconds=30,
        otp_length=6,
        max_attempts=3,
        max_resends=3,
        provider_enabled=True,
        mock_simulation_mode=SimulationMode.SUCCESS,
        mock_execution_delay_ms=0,
        mock_allow_random=False,
        provider_audit_enabled=True,
        provider_metrics_enabled=True,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


@override_settings(SECRET_KEY="test-secret-key-for-msg91-provider")
class Msg91ProviderTests(SimpleTestCase):
    def setUp(self):
        reset_otp_process_storage()
        self.backend = CaptureBackend()
        self.audit = AuditLogger(backend=self.backend)
        self.transport = MagicMock(spec=RequestsHttpTransport)

    def _runtime(self, *, configuration: OTPConfiguration, transport=None):
        engine = build_otp_engine(
            configuration=configuration,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
            audit_logger=self.audit,
        )
        return build_otp_provider_runtime(
            configuration=configuration,
            engine=engine,
            audit_logger=self.audit,
            transport=transport,
        )

    def test_configuration_validation_requires_msg91_fields(self):
        with self.assertRaises(ConfigurationException):
            validate_msg91_configuration(_msg91_config(msg91_auth_key=""))
        with self.assertRaises(ConfigurationException):
            validate_msg91_configuration(
                _msg91_config(msg91_base_url="http://insecure.example/api/v5/flow/")
            )

    def test_provider_init_fails_fast_on_missing_config(self):
        with self.assertRaises(ConfigurationException):
            Msg91SmsProvider(
                configuration=_msg91_config(msg91_flow_id=""),
                audit_logger=self.audit,
                transport=self.transport,
            )

    def test_https_enforced_by_transport(self):
        real_transport = RequestsHttpTransport()
        with self.assertRaises(SecurityException):
            real_transport.post_json(
                url="http://api.msg91.com/api/v5/flow/",
                headers={"authkey": "x"},
                payload={},
                timeout_seconds=1,
            )

    def test_phone_normalization(self):
        provider = Msg91SmsProvider(
            configuration=_msg91_config(),
            audit_logger=self.audit,
            transport=self.transport,
        )
        self.assertEqual(provider.normalize_destination("+919876543210"), "919876543210")
        self.assertEqual(provider.normalize_destination("9876543210"), "919876543210")
        self.assertEqual(provider.normalize_destination("91-98765-43210"), "919876543210")
        with self.assertRaises(InvalidPhoneException):
            provider.normalize_destination("abc")

    def test_request_mapping_payload(self):
        provider = Msg91SmsProvider(
            configuration=_msg91_config(),
            audit_logger=self.audit,
            transport=self.transport,
        )
        request = ProviderRequest(
            destination="+919876543210",
            message="123456",
            channel=DeliveryChannel.SMS,
            metadata={"challenge_id": "c1"},
        )
        payload = provider.build_payload(
            request=request,
            mobile=provider.normalize_destination(request.destination),
        )
        self.assertEqual(payload["flow_id"], "flow-123")
        self.assertEqual(payload["sender"], "NITYAD")
        self.assertEqual(payload["recipients"][0]["mobiles"], "919876543210")
        self.assertEqual(payload["recipients"][0]["OTP"], "123456")
        headers = provider.build_headers()
        self.assertEqual(headers["authkey"], "test-auth-key")
        self.assertEqual(headers["content-type"], "application/json")

    def test_successful_send_maps_response(self):
        self.transport.post_json.return_value = HttpTransportResult(
            status_code=200,
            payload={"type": "success", "message": "ref-abc"},
            raw_text='{"type":"success","message":"ref-abc"}',
        )
        provider = Msg91SmsProvider(
            configuration=_msg91_config(),
            audit_logger=self.audit,
            transport=self.transport,
        )
        response = provider.send(
            ProviderRequest(
                destination="9876543210",
                message="654321",
                channel=DeliveryChannel.SMS,
                metadata={"challenge_id": "c1"},
            )
        )
        self.assertTrue(response.accepted)
        self.assertEqual(response.provider_reference, "ref-abc")
        self.assertEqual(response.provider_name, constants.PROVIDER_MSG91)
        called = self.transport.post_json.call_args.kwargs
        self.assertEqual(called["payload"]["recipients"][0]["OTP"], "654321")
        self.assertTrue(str(called["url"]).startswith("https://"))

    def test_msg91_error_response_raises_failure(self):
        self.transport.post_json.return_value = HttpTransportResult(
            status_code=200,
            payload={"type": "error", "message": "flow id missing"},
            raw_text='{"type":"error"}',
        )
        provider = Msg91SmsProvider(
            configuration=_msg91_config(),
            audit_logger=self.audit,
            transport=self.transport,
        )
        with self.assertRaises(ProviderFailureException):
            provider.send(
                ProviderRequest(
                    destination="9876543210",
                    message="111111",
                    channel=DeliveryChannel.SMS,
                    metadata={},
                )
            )

    def test_timeout_translation(self):
        self.transport.post_json.side_effect = TransportTimeoutError("timed out")
        provider = Msg91SmsProvider(
            configuration=_msg91_config(),
            audit_logger=self.audit,
            transport=self.transport,
        )
        with self.assertRaises(ProviderTimeoutException):
            provider.send(
                ProviderRequest(
                    destination="9876543210",
                    message="111111",
                    channel=DeliveryChannel.SMS,
                    metadata={},
                )
            )

    def test_auth_failure_translation(self):
        self.transport.post_json.side_effect = TransportAuthenticationError(
            "auth failed",
            status_code=401,
        )
        provider = Msg91SmsProvider(
            configuration=_msg91_config(),
            audit_logger=self.audit,
            transport=self.transport,
        )
        with self.assertRaises(ProviderAuthenticationException):
            provider.send(
                ProviderRequest(
                    destination="9876543210",
                    message="111111",
                    channel=DeliveryChannel.SMS,
                    metadata={},
                )
            )

    def test_unavailable_translation(self):
        self.transport.post_json.side_effect = TransportUnavailableError(
            "down",
            status_code=503,
        )
        provider = Msg91SmsProvider(
            configuration=_msg91_config(),
            audit_logger=self.audit,
            transport=self.transport,
        )
        with self.assertRaises(ProviderUnavailableException):
            provider.send(
                ProviderRequest(
                    destination="9876543210",
                    message="111111",
                    channel=DeliveryChannel.SMS,
                    metadata={},
                )
            )

    def test_malformed_response(self):
        self.transport.post_json.return_value = HttpTransportResult(
            status_code=200,
            payload={"hello": "world"},
            raw_text="{}",
        )
        provider = Msg91SmsProvider(
            configuration=_msg91_config(),
            audit_logger=self.audit,
            transport=self.transport,
        )
        with self.assertRaises(InvalidProviderResponseException):
            provider.send(
                ProviderRequest(
                    destination="9876543210",
                    message="111111",
                    channel=DeliveryChannel.SMS,
                    metadata={},
                )
            )

    def test_audit_never_contains_secrets(self):
        self.transport.post_json.return_value = HttpTransportResult(
            status_code=200,
            payload={"type": "success", "message": "ref-1"},
            raw_text="",
        )
        provider = Msg91SmsProvider(
            configuration=_msg91_config(),
            audit_logger=self.audit,
            transport=self.transport,
        )
        provider.send(
            ProviderRequest(
                destination="9876543210",
                message="999888",
                channel=DeliveryChannel.SMS,
                metadata={"challenge_id": "c9"},
            )
        )
        forbidden = {
            "otp",
            "otp_code",
            "message",
            "headers",
            "authkey",
            "auth_key",
            "flow_id",
            "sender_id",
            "request_body",
            "response_body",
            "payload",
        }
        for event in self.backend.events:
            self.assertTrue(forbidden.isdisjoint(event["metadata"].keys()))
            blob = str(event["metadata"])
            self.assertNotIn("999888", blob)
            self.assertNotIn("test-auth-key", blob)
            self.assertNotIn("flow-123", blob)

    def test_registry_and_di_resolution(self):
        runtime = self._runtime(configuration=_msg91_config(), transport=self.transport)
        self.assertTrue(runtime.registry.has_provider(constants.PROVIDER_MSG91))
        self.assertTrue(runtime.registry.has_provider(constants.PROVIDER_MOCK_SMS))
        self.assertIsInstance(runtime.provider, Msg91SmsProvider)

    def test_provider_switching_by_configuration(self):
        mock_runtime = self._runtime(configuration=_mock_config())
        self.assertIsInstance(mock_runtime.provider, MockOTPProvider)

        self.transport.post_json.return_value = HttpTransportResult(
            status_code=200,
            payload={"type": "success", "message": "ref-switch"},
            raw_text="",
        )
        msg91_runtime = self._runtime(configuration=_msg91_config(), transport=self.transport)
        self.assertIsInstance(msg91_runtime.provider, Msg91SmsProvider)
        result = msg91_runtime.orchestrator.deliver_otp(
            flow_type="user_registration",
            destination="9876543210",
            context={},
        )
        self.assertEqual(result.provider_result.status, ProviderResultStatus.SUCCESS)
        stored = msg91_runtime.engine.repository.get_by_id(result.challenge.id)
        self.assertNotIn("otp_code", stored.__dataclass_fields__)

    def test_end_to_end_transient_otp_not_in_result(self):
        self.transport.post_json.return_value = HttpTransportResult(
            status_code=200,
            payload={"type": "success", "message": "ref-e2e"},
            raw_text="",
        )
        runtime = self._runtime(configuration=_msg91_config(), transport=self.transport)
        delivery = runtime.orchestrator.deliver_otp(
            flow_type="user_registration",
            destination="+919876543210",
            context={},
        )
        self.assertFalse(hasattr(delivery.challenge, "otp_code"))
        self.assertNotIn("otp", delivery.provider_result.__dataclass_fields__)
        # Ensure transport received OTP only in payload (mocked), not returned outward.
        sent_otp = self.transport.post_json.call_args.kwargs["payload"]["recipients"][0]["OTP"]
        self.assertTrue(sent_otp.isdigit())
        self.assertEqual(len(sent_otp), 6)

    def test_transport_maps_http_status_codes(self):
        from otp_verification.transport.exceptions import TransportRateLimitError

        transport = RequestsHttpTransport()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.content = b"{}"
        mock_resp.text = "{}"
        mock_resp.json.return_value = {}
        with patch.object(transport._session, "post", return_value=mock_resp):
            with self.assertRaises(TransportRateLimitError):
                transport.post_json(
                    url="https://control.msg91.com/api/v5/flow/",
                    headers={"authkey": "x"},
                    payload={"a": 1},
                    timeout_seconds=1,
                )
