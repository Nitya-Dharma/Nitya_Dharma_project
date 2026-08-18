"""Unit tests for RegistrationOTPService facade (no registration view wiring)."""

from __future__ import annotations

from django.test import SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.registration import (
    RegistrationOTPDeliveryFailed,
    RegistrationOTPDisabled,
    RegistrationOTPInvalid,
    RegistrationOTPValidationError,
    build_registration_otp_service,
)
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.security.contracts import ReplayProtection
from otp_verification.storage.memory import InMemoryChallengeRepository


def _config(**overrides) -> OTPConfiguration:
    base = dict(
        enabled=True,
        mode="mock",
        provider=constants.PROVIDER_MOCK_SMS,
        enabled_flows=constants.FLOW_CHOICES,
        otp_expiry_seconds=600,
        resend_cooldown_seconds=60,
        otp_length=6,
        max_attempts=5,
        max_resends=3,
        provider_enabled=True,
        mock_simulation_mode=SimulationMode.SUCCESS.value,
        mock_execution_delay_ms=0,
        mock_allow_random=False,
        provider_audit_enabled=True,
        provider_metrics_enabled=True,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


@override_settings(
    SECRET_KEY="test-secret-key-for-registration-otp",
    OTP_CHALLENGE_STORAGE="memory",
)
class RegistrationOTPServiceTests(SimpleTestCase):
    def setUp(self):
        reset_otp_process_storage()

    def _runtime(self, **overrides):
        config = _config(**overrides)
        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
        )
        return build_otp_provider_runtime(configuration=config, engine=engine)

    def test_is_enabled_for_flow_respects_feature_flag(self):
        service_off = build_registration_otp_service(configuration=_config(enabled=False))
        self.assertFalse(service_off.is_enabled_for_flow(constants.FLOW_BUREAU_REGISTRATION))

        service_on = build_registration_otp_service(configuration=_config(enabled=True))
        self.assertTrue(service_on.is_enabled_for_flow(constants.FLOW_BUREAU_REGISTRATION))

        service_filtered = build_registration_otp_service(
            configuration=_config(
                enabled=True,
                enabled_flows=(constants.FLOW_BUREAU_REGISTRATION,),
            )
        )
        self.assertTrue(service_filtered.is_enabled_for_flow(constants.FLOW_BUREAU_REGISTRATION))
        self.assertFalse(service_filtered.is_enabled_for_flow(constants.FLOW_PANDIT_REGISTRATION))

    def test_start_and_verify_happy_path(self):
        runtime = self._runtime()
        service = build_registration_otp_service(runtime=runtime)

        issued = service.start_verification(
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            destination="9876543210",
            context={"email": "bureau@example.com"},
        )
        self.assertTrue(issued.challenge_id)
        self.assertEqual(issued.flow_type, constants.FLOW_BUREAU_REGISTRATION)

        # Recover transient OTP from engine repo is impossible (hash only).
        # Use orchestrator path: create via manager for known code in unit test by
        # reading challenge and verifying with a wrong code then success via mock runtime:
        # Issue again through challenge manager to capture otp_code for assert.
        from otp_verification.services.core import ChallengeManager

        mgr: ChallengeManager = runtime.engine.challenge_manager
        issued2 = mgr.create_challenge(
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            context={"canonical_phone": "9876543210"},
        )
        verified = service.verify_challenge(
            challenge_id=issued2.challenge.id,
            submitted_otp=issued2.otp_code,
        )
        self.assertEqual(verified.challenge_id, issued2.challenge.id)
        self.assertEqual(verified.status, "VERIFIED")

    def test_invalid_otp_maps_to_registration_exception(self):
        runtime = self._runtime()
        service = build_registration_otp_service(runtime=runtime)
        issued = runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        with self.assertRaises(RegistrationOTPInvalid):
            service.verify_challenge(
                challenge_id=issued.challenge.id,
                submitted_otp="000000",
            )

    def test_disabled_flow_raises(self):
        service = build_registration_otp_service(configuration=_config(enabled=False))
        with self.assertRaises(RegistrationOTPDisabled):
            service.start_verification(
                flow_type=constants.FLOW_PANDIT_REGISTRATION,
                destination="9876543210",
            )

    def test_invalid_phone_raises_validation(self):
        service = build_registration_otp_service(configuration=_config())
        with self.assertRaises(RegistrationOTPValidationError):
            service.start_verification(
                flow_type=constants.FLOW_BUREAU_REGISTRATION,
                destination="abc",
            )

    def test_provider_failure_maps_to_delivery_failed(self):
        runtime = self._runtime(mock_simulation_mode=SimulationMode.FAILURE.value)
        service = build_registration_otp_service(runtime=runtime)
        with self.assertRaises(RegistrationOTPDeliveryFailed):
            service.start_verification(
                flow_type=constants.FLOW_BUREAU_REGISTRATION,
                destination="9876543210",
            )

    def test_issue_result_exposes_no_provider_fields(self):
        runtime = self._runtime()
        service = build_registration_otp_service(runtime=runtime)
        issued = service.start_verification(
            flow_type=constants.FLOW_EXPERT_REGISTRATION,
            destination="9876543210",
        )
        payload = issued.__dict__
        for forbidden in ("provider_result", "otp_code", "message", "auth_key", "headers"):
            self.assertNotIn(forbidden, payload)

    def test_process_scoped_store_survives_separate_service_builders(self):
        """Issue and verify must work across independent DI builds (same worker)."""

        reset_otp_process_storage()
        runtime_a = build_otp_provider_runtime(configuration=_config())
        created = runtime_a.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        runtime_b = build_otp_provider_runtime(configuration=_config())
        self.assertIs(runtime_a.engine.repository, runtime_b.engine.repository)
        verified = runtime_b.engine.challenge_manager.verify_challenge(
            challenge_id=created.challenge.id,
            submitted_otp=created.otp_code,
        )
        self.assertEqual(verified.status, "VERIFIED")
