"""Unit tests for mock provider, simulation, lifecycle, and orchestration."""

from __future__ import annotations

from django.test import SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import (
    DeliveryChannel,
    ProviderLifecycleStatus,
    ProviderResultStatus,
    SimulationMode,
)
from otp_verification.exceptions import (
    ProviderDisabledException,
    ProviderFailureException,
    ProviderNotFoundException,
    ProviderTimeoutException,
    ProviderUnavailableException,
    ValidationException,
)
from otp_verification.interfaces.providers import ProviderRequest
from otp_verification.providers.base import ProviderDescriptor
from otp_verification.providers.lifecycle import ProviderLifecycle
from otp_verification.providers.mock import MockOTPProvider
from otp_verification.providers.registry import OTPProviderRegistry
from otp_verification.providers.resolver import ProviderResolver
from otp_verification.providers.results import ProviderResult, validate_provider_result
from otp_verification.services.factory import build_otp_engine, build_otp_provider_runtime, reset_otp_process_storage
from otp_verification.services.support import AuditLogger, NullLoggingBackend
from otp_verification.logging.contracts import AuditEventPayload, LoggingBackend
from otp_verification.security.contracts import ReplayProtection
from otp_verification.storage.memory import InMemoryChallengeRepository


class CaptureBackend(LoggingBackend):
    def __init__(self) -> None:
        self.events: list[dict] = []

    def emit(self, payload: AuditEventPayload) -> None:
        self.events.append({"event": payload.event, "metadata": dict(payload.metadata)})


def _config(**overrides) -> OTPConfiguration:
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


def _isolated_runtime(*, configuration: OTPConfiguration, audit_logger=None):
    """Build a runtime with isolated challenge storage (no process singleton)."""

    engine = build_otp_engine(
        configuration=configuration,
        repository=InMemoryChallengeRepository(),
        replay_protector=ReplayProtection(),
        audit_logger=audit_logger,
    )
    return build_otp_provider_runtime(
        configuration=configuration,
        engine=engine,
        audit_logger=audit_logger,
    )


@override_settings(SECRET_KEY="test-secret-key-for-otp-provider")
class MockProviderTests(SimpleTestCase):
    def setUp(self):
        reset_otp_process_storage()
        self.backend = CaptureBackend()
        self.audit = AuditLogger(backend=self.backend)

    def test_provider_registration_and_discovery(self):
        runtime = _isolated_runtime(configuration=_config(), audit_logger=self.audit)
        self.assertTrue(runtime.registry.has_provider(constants.PROVIDER_MOCK_SMS))
        names = runtime.registry.list_providers()
        self.assertIn(constants.PROVIDER_MOCK_SMS, names)
        discovered = runtime.resolver.discover()
        self.assertEqual(discovered[0].dotted_path, constants.MOCK_PROVIDER_DOTTED_PATH)

    def test_provider_resolution_via_registry_factory(self):
        runtime =  _isolated_runtime(configuration=_config(), audit_logger=self.audit)
        provider = runtime.resolver.resolve(constants.PROVIDER_MOCK_SMS)
        self.assertIsInstance(provider, MockOTPProvider)
        self.assertEqual(provider.provider_name, constants.PROVIDER_MOCK_SMS)

    def test_unknown_provider_raises(self):
        runtime =  _isolated_runtime(configuration=_config(), audit_logger=self.audit)
        with self.assertRaises(ProviderNotFoundException):
            runtime.resolver.resolve("does_not_exist")

    def test_successful_send_no_network(self):
        provider = MockOTPProvider(configuration=_config(), audit_logger=self.audit)
        response = provider.send(
            ProviderRequest(
                destination="+919999999999",
                message="123456",
                channel=DeliveryChannel.SMS,
                metadata={"challenge_id": "c1"},
            )
        )
        self.assertTrue(response.accepted)
        self.assertEqual(response.provider_name, constants.PROVIDER_MOCK_SMS)
        self.assertIsNotNone(response.provider_reference)
        self.assertNotIn("123456", str(response.metadata))

    def test_failure_simulation(self):
        provider = MockOTPProvider(
            configuration=_config(mock_simulation_mode=SimulationMode.FAILURE),
            audit_logger=self.audit,
        )
        with self.assertRaises(ProviderFailureException):
            provider.send(
                ProviderRequest(
                    destination="+919999999999",
                    message="123456",
                    channel=DeliveryChannel.SMS,
                    metadata={},
                )
            )

    def test_timeout_simulation(self):
        provider = MockOTPProvider(
            configuration=_config(mock_simulation_mode=SimulationMode.TIMEOUT),
            audit_logger=self.audit,
        )
        with self.assertRaises(ProviderTimeoutException):
            provider.send(
                ProviderRequest(
                    destination="+919999999999",
                    message="123456",
                    channel=DeliveryChannel.SMS,
                    metadata={},
                )
            )

    def test_unavailable_simulation(self):
        provider = MockOTPProvider(
            configuration=_config(mock_simulation_mode=SimulationMode.UNAVAILABLE),
            audit_logger=self.audit,
        )
        with self.assertRaises(ProviderUnavailableException):
            provider.send(
                ProviderRequest(
                    destination="+919999999999",
                    message="123456",
                    channel=DeliveryChannel.SMS,
                    metadata={},
                )
            )

    def test_disabled_provider(self):
        provider = MockOTPProvider(
            configuration=_config(provider_enabled=False),
            audit_logger=self.audit,
        )
        self.assertEqual(provider.lifecycle.status, ProviderLifecycleStatus.DISABLED)
        with self.assertRaises(ProviderDisabledException):
            provider.send(
                ProviderRequest(
                    destination="+919999999999",
                    message="123456",
                    channel=DeliveryChannel.SMS,
                    metadata={},
                )
            )

    def test_illegal_lifecycle_transition(self):
        lifecycle = ProviderLifecycle()
        with self.assertRaises(ValidationException):
            lifecycle.transition_to(ProviderLifecycleStatus.SUCCESS)

    def test_provider_result_validation(self):
        from datetime import datetime, timezone

        result = ProviderResult(
            status=ProviderResultStatus.SUCCESS,
            provider_name="mock_sms",
            provider_message="ok",
            provider_reference="mock-1",
            timestamp=datetime.now(timezone.utc),
        )
        self.assertTrue(validate_provider_result(result).is_success())
        with self.assertRaises(Exception):
            validate_provider_result(
                ProviderResult(
                    status="not-a-status",
                    provider_name="mock_sms",
                    provider_message="ok",
                    provider_reference="mock-1",
                    timestamp=datetime.now(timezone.utc),
                )
            )

    def test_metrics_update_on_success(self):
        runtime =  _isolated_runtime(configuration=_config(), audit_logger=self.audit)
        runtime.provider.send(
            ProviderRequest(
                destination="+919999999999",
                message="123456",
                channel=DeliveryChannel.SMS,
                metadata={},
            )
        )
        snap = runtime.metrics.snapshot()
        self.assertEqual(snap.total_executions, 1)
        self.assertEqual(snap.successful_executions, 1)

    def test_audit_generation_excludes_secrets(self):
        provider = MockOTPProvider(configuration=_config(), audit_logger=self.audit)
        provider.send(
            ProviderRequest(
                destination="+919999999999",
                message="654321",
                channel=DeliveryChannel.SMS,
                metadata={"challenge_id": "abc"},
            )
        )
        self.assertTrue(self.backend.events)
        for event in self.backend.events:
            meta = event["metadata"]
            forbidden = {"otp", "otp_code", "otp_hash", "hash", "salt", "message"}
            self.assertTrue(forbidden.isdisjoint(meta.keys()))
            blob = str(meta)
            self.assertNotIn("654321", blob)

    def test_orchestration_success_handoff(self):
        runtime =  _isolated_runtime(configuration=_config(), audit_logger=self.audit)
        result = runtime.orchestrator.deliver_otp(
            flow_type="user_registration",
            destination="+919999999999",
            context={},
        )
        self.assertEqual(result.provider_result.status, ProviderResultStatus.SUCCESS)
        self.assertEqual(result.challenge.flow_type, "user_registration")
        stored = runtime.engine.repository.get_by_id(result.challenge.id)
        self.assertFalse(hasattr(stored, "otp_code"))
        self.assertNotIn("otp_code", stored.__dataclass_fields__)

    def test_orchestration_failure_propagates(self):
        runtime =  _isolated_runtime(configuration=_config(mock_simulation_mode=SimulationMode.FAILURE), audit_logger=self.audit)
        with self.assertRaises(ProviderFailureException):
            runtime.orchestrator.deliver_otp(
                flow_type="user_registration",
                destination="+919999999999",
                context={},
            )

    def test_no_http_libraries_imported_by_mock_module(self):
        import otp_verification.providers.mock as mock_mod
        import otp_verification.providers.simulation as sim_mod
        import otp_verification.services.orchestration as orch_mod

        for module in (mock_mod, sim_mod, orch_mod):
            for banned in ("requests", "httpx", "urllib", "socket", "twilio"):
                self.assertNotIn(banned, module.__dict__)
