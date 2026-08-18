"""Unit tests for registration OTP resend (Task 7B-I / 7B-II)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.exceptions import ProviderFailureException
from otp_verification.registration.exceptions import (
    RegistrationOTPCooldownActive,
    RegistrationOTPGenerationLimitReached,
    RegistrationOTPLocked,
    RegistrationOTPReplay,
    RegistrationOTPValidationError,
)
from otp_verification.registration.factory import build_registration_otp_resend_service
from otp_verification.registration.responses import (
    ERROR_COOLDOWN,
    ERROR_GENERATION_LIMIT,
    ERROR_OWNERSHIP,
)
from otp_verification.registration.session import (
    PENDING_SESSION_KEY,
    get_otp_generation_count,
    get_pending_registration,
    mark_registration_otp_verified,
    record_successful_otp_generation,
    store_pending_registration,
)
from otp_verification.registration.views import resend_registration_otp
from otp_verification.security.contracts import ReplayProtection
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.storage.memory import InMemoryChallengeRepository


def _config(**overrides) -> OTPConfiguration:
    base = dict(
        enabled=True,
        mode="mock",
        provider=constants.PROVIDER_MOCK_SMS,
        enabled_flows=constants.FLOW_CHOICES,
        otp_expiry_seconds=600,
        resend_cooldown_seconds=30,
        otp_length=6,
        max_attempts=5,
        max_resends=3,
        provider_enabled=True,
        mock_simulation_mode=SimulationMode.SUCCESS.value,
        mock_execution_delay_ms=0,
        mock_allow_random=False,
        provider_audit_enabled=True,
        provider_metrics_enabled=True,
        registration_pending_ttl_seconds=900,
        registration_completed_ttl_seconds=1800,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


def _prepare_request(factory, *, data=None):
    request = factory.post("/otp/registration/resend/", data=data or {})
    request.session = SessionStore()
    request._messages = FallbackStorage(request)
    request.META["HTTP_ACCEPT"] = "application/json"
    return request


def _json(response):
    return json.loads(response.content.decode("utf-8"))


@override_settings(
    SECRET_KEY="test-secret-key-for-otp-resend",
    ROOT_URLCONF="nityadharma.urls",
    OTP_ENABLED=True,
    OTP_PROVIDER=constants.PROVIDER_MOCK_SMS,
    OTP_RESEND_COOLDOWN_SECONDS=30,
    OTP_MAX_RESENDS=3,
)
class RegistrationOTPResendTests(SimpleTestCase):
    def setUp(self):
        reset_otp_process_storage()
        self.factory = RequestFactory()
        self.config = _config(resend_cooldown_seconds=0, max_resends=3)
        engine = build_otp_engine(
            configuration=self.config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
        )
        self.runtime = build_otp_provider_runtime(configuration=self.config, engine=engine)
        self.resend_service = build_registration_otp_resend_service(
            runtime=self.runtime,
            configuration=self.config,
        )

    def _store_with_challenge(self, request, *, challenge_id, last_resent_at=None):
        store_pending_registration(
            request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            challenge_id=challenge_id,
            destination="9876543210",
            payload={"email": "resend@example.com", "password": "Secret123!"},
            resume_path="/accounts/register/",
        )
        if last_resent_at is not None:
            pending = request.session[PENDING_SESSION_KEY]
            pending["last_resent_at"] = last_resent_at
            request.session[PENDING_SESSION_KEY] = pending

    def test_successful_resend_rebinds_challenge(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(
            self.factory,
            data={"challenge_id": issued.challenge.id},
        )
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        result = self.resend_service.resend(
            request,
            posted_challenge_id=issued.challenge.id,
        )
        pending = get_pending_registration(request)
        self.assertNotEqual(result.challenge_id, issued.challenge.id)
        self.assertEqual(pending["challenge_id"], result.challenge_id)
        self.assertEqual(pending["resend_count"], 1)
        self.assertEqual(result.remaining_attempts, 3)
        self.assertEqual(
            get_otp_generation_count(
                request, flow_type=constants.FLOW_USER_REGISTRATION
            ),
            2,
        )

    def test_ownership_failure(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory, data={"challenge_id": "forged"})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        with self.assertRaises(RegistrationOTPValidationError):
            self.resend_service.resend(request, posted_challenge_id="forged")

    def test_cooldown_active(self):
        config = _config(resend_cooldown_seconds=60, max_resends=3)
        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
        )
        runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        service = build_registration_otp_resend_service(runtime=runtime, configuration=config)
        issued = runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory, data={"challenge_id": issued.challenge.id})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        with self.assertRaises(RegistrationOTPCooldownActive) as ctx:
            service.resend(request, posted_challenge_id=issued.challenge.id)
        self.assertGreater(ctx.exception.remaining_seconds, 0)

    def test_generation_limit_reached(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory, data={"challenge_id": issued.challenge.id})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        for _ in range(constants.MAX_OTP_GENERATIONS_PER_SESSION - 1):
            record_successful_otp_generation(
                request, flow_type=constants.FLOW_USER_REGISTRATION
            )
        with self.assertRaises(RegistrationOTPGenerationLimitReached):
            self.resend_service.resend(request, posted_challenge_id=issued.challenge.id)

    def test_locked_challenge_denied(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        for _ in range(5):
            try:
                self.runtime.engine.challenge_manager.verify_challenge(
                    challenge_id=issued.challenge.id,
                    submitted_otp="000000",
                )
            except Exception:
                pass
        request = _prepare_request(self.factory, data={"challenge_id": issued.challenge.id})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        with self.assertRaises(RegistrationOTPLocked):
            self.resend_service.resend(request, posted_challenge_id=issued.challenge.id)

    def test_verified_marker_blocks_resend(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory, data={"challenge_id": issued.challenge.id})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        mark_registration_otp_verified(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_USER_REGISTRATION,
        )
        with self.assertRaises(RegistrationOTPReplay):
            self.resend_service.resend(request, posted_challenge_id=issued.challenge.id)

    def test_expired_challenge_allows_new_challenge(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        record = self.runtime.engine.challenge_manager.repository.get_by_id(issued.challenge.id)
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        updated = record.copy_with(expires_at=past, updated_at=past)
        self.runtime.engine.challenge_manager.repository.update(
            issued.challenge.id, payload={"record": updated}
        )
        request = _prepare_request(self.factory, data={"challenge_id": issued.challenge.id})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        result = self.resend_service.resend(
            request,
            posted_challenge_id=issued.challenge.id,
        )
        self.assertNotEqual(result.challenge_id, issued.challenge.id)

    def test_provider_failure_mapped(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory, data={"challenge_id": issued.challenge.id})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        with patch.object(
            self.runtime.orchestrator,
            "deliver_otp",
            side_effect=ProviderFailureException("boom"),
        ):
            with self.assertRaises(Exception):
                self.resend_service.resend(request, posted_challenge_id=issued.challenge.id)
        self.assertEqual(
            get_otp_generation_count(
                request, flow_type=constants.FLOW_USER_REGISTRATION
            ),
            1,
        )

    def test_view_cooldown_json(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory, data={"challenge_id": issued.challenge.id})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_resend_service",
            return_value=build_registration_otp_resend_service(
                runtime=self.runtime,
                configuration=_config(resend_cooldown_seconds=60),
            ),
        ):
            response = resend_registration_otp(request)
        body = _json(response)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(body["error"], ERROR_COOLDOWN)
        self.assertIn("remaining_seconds", body)

    def test_view_ownership_json(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory, data={"challenge_id": "forged"})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_resend_service",
            return_value=self.resend_service,
        ):
            response = resend_registration_otp(request)
        body = _json(response)
        self.assertEqual(body["error"], ERROR_OWNERSHIP)

    def test_view_generation_limit_json(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory, data={"challenge_id": issued.challenge.id})
        self._store_with_challenge(request, challenge_id=issued.challenge.id)
        for _ in range(constants.MAX_OTP_GENERATIONS_PER_SESSION - 1):
            record_successful_otp_generation(
                request, flow_type=constants.FLOW_USER_REGISTRATION
            )
        with patch(
            "otp_verification.registration.views.build_registration_otp_resend_service",
            return_value=self.resend_service,
        ):
            response = resend_registration_otp(request)
        body = _json(response)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(body["error"], ERROR_GENERATION_LIMIT)

    def test_duplicate_resend_after_success_hits_cooldown_when_enabled(self):
        config = _config(resend_cooldown_seconds=30, max_resends=5)
        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
        )
        runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        service = build_registration_otp_resend_service(runtime=runtime, configuration=config)
        issued = runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = _prepare_request(self.factory, data={"challenge_id": issued.challenge.id})
        # Pretend cooldown already elapsed so first resend succeeds.
        past = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        self._store_with_challenge(
            request,
            challenge_id=issued.challenge.id,
            last_resent_at=past,
        )
        first = service.resend(request, posted_challenge_id=issued.challenge.id)
        with self.assertRaises(RegistrationOTPCooldownActive):
            service.resend(request, posted_challenge_id=first.challenge_id)
