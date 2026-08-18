"""Unit tests for registration consuming phone_verified (Phase 3 Task 2 Part D)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import ChallengeStatus, SimulationMode
from otp_verification.registration.gate import begin_otp_or_continue
from otp_verification.registration.session import (
    PHONE_CHALLENGE_SESSION_KEY,
    PHONE_VERIFIED_SESSION_KEY,
    consume_phone_verified_session,
    get_phone_verified,
    phone_verified_matches_registration,
    store_phone_challenge,
    store_phone_verified,
)
from otp_verification.security.contracts import ReplayProtection
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.services.support import AuditLogger, NullLoggingBackend
from otp_verification.storage.memory import InMemoryChallengeRepository
from otp_verification.registration.factory import build_registration_otp_service


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
        registration_pending_ttl_seconds=900,
        registration_completed_ttl_seconds=1800,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


@override_settings(
    SECRET_KEY="test-secret-key-for-phone-verified-consume",
    OTP_CHALLENGE_STORAGE="memory",
    OTP_ENABLED=True,
    OTP_PROVIDER=constants.PROVIDER_MOCK_SMS,
    OTP_REGISTRATION_PENDING_TTL_SECONDS=900,
)
class RegistrationConsumesPhoneVerifiedTests(SimpleTestCase):
    def setUp(self):
        reset_otp_process_storage()
        self.factory = RequestFactory()
        self.config = _config()
        self.engine = build_otp_engine(
            configuration=self.config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        self.runtime = build_otp_provider_runtime(
            configuration=self.config,
            engine=self.engine,
        )
        self.service = build_registration_otp_service(
            runtime=self.runtime,
            configuration=self.config,
        )

    def tearDown(self):
        reset_otp_process_storage()

    def _request(self, *, wants_json: bool = False):
        request = self.factory.post("/accounts/register/")
        request.session = SessionStore()
        if wants_json:
            request.META["HTTP_ACCEPT"] = "application/json"
        return request

    def _issue_and_verify(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        self.service.verify_challenge(
            challenge_id=issued.challenge.id,
            submitted_otp=issued.otp_code,
        )
        return issued

    def _seed_verified(self, request, *, challenge_id: str, destination="9876543210", flow=None):
        store_phone_challenge(
            request,
            challenge_id=challenge_id,
            flow_type=flow or constants.FLOW_USER_REGISTRATION,
            destination=destination,
        )
        # store_phone_challenge clears phone_verified — store proof after challenge seed.
        store_phone_verified(
            request,
            challenge_id=challenge_id,
            destination=destination,
            flow_type=flow or constants.FLOW_USER_REGISTRATION,
        )

    def _assert_otp_fallback(self, *, request, flow_type, destination, resume_path, payload=None):
        mock_issued = MagicMock()
        mock_issued.challenge_id = "fallback"
        mock_issued.flow_type = flow_type
        mock_issued.expires_at = datetime.now(timezone.utc)
        mock_service = MagicMock()
        mock_service.start_verification.return_value = mock_issued
        # Challenge-status probes may also call the factory.
        mock_service.get_challenge_status.side_effect = Exception("unused")
        with patch(
            "otp_verification.registration.gate.build_registration_otp_service",
            return_value=mock_service,
        ):
            response = begin_otp_or_continue(
                request,
                flow_type=flow_type,
                destination=destination,
                payload=payload or {"email": "a@example.com", "password": "Secret123!"},
                resume_path=resume_path,
                wants_json=True,
            )
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 202)
        mock_service.start_verification.assert_called_once()
        return response

    def test_verified_phone_skips_second_otp(self):
        issued = self._issue_and_verify()
        request = self._request()
        self._seed_verified(request, challenge_id=issued.challenge.id)
        mock_service = MagicMock()
        mock_service.get_challenge_status = self.service.get_challenge_status
        with patch(
            "otp_verification.registration.gate.build_registration_otp_service",
            return_value=self.service,
        ):
            response = begin_otp_or_continue(
                request,
                flow_type=constants.FLOW_USER_REGISTRATION,
                destination="9876543210",
                payload={"email": "a@example.com", "password": "Secret123!"},
                resume_path="/accounts/register/",
            )
        self.assertIsNone(response)
        self.assertIsNotNone(get_phone_verified(request))
        self.assertNotIn("otp.registration.pending", request.session)

    def test_missing_verified_uses_existing_otp_flow(self):
        request = self._request()
        self._assert_otp_fallback(
            request=request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            destination="9876543210",
            resume_path="/accounts/register/",
        )

    def test_expired_verified_falls_back_to_otp(self):
        issued = self._issue_and_verify()
        request = self._request()
        self._seed_verified(request, challenge_id=issued.challenge.id)
        data = request.session[PHONE_VERIFIED_SESSION_KEY]
        data["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        request.session[PHONE_VERIFIED_SESSION_KEY] = data
        self._assert_otp_fallback(
            request=request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            destination="9876543210",
            resume_path="/accounts/register/",
        )

    def test_wrong_phone_falls_back_to_otp(self):
        issued = self._issue_and_verify()
        request = self._request()
        self._seed_verified(request, challenge_id=issued.challenge.id, destination="9876543210")
        self._assert_otp_fallback(
            request=request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            destination="9123456780",
            resume_path="/accounts/register/",
        )

    def test_wrong_flow_falls_back_to_otp(self):
        issued = self._issue_and_verify()
        request = self._request()
        self._seed_verified(
            request,
            challenge_id=issued.challenge.id,
            flow=constants.FLOW_USER_REGISTRATION,
        )
        self._assert_otp_fallback(
            request=request,
            flow_type=constants.FLOW_BUREAU_REGISTRATION,
            destination="9876543210",
            resume_path="/bureaus/register/",
        )

    def test_tampered_session_falls_back_to_otp(self):
        request = self._request()
        request.session[PHONE_VERIFIED_SESSION_KEY] = {
            "challenge_id": "",
            "destination": "9876543210",
            "flow_type": constants.FLOW_USER_REGISTRATION,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        }
        self.assertIsNone(
            phone_verified_matches_registration(
                request,
                flow_type=constants.FLOW_USER_REGISTRATION,
                destination="9876543210",
            )
        )
        self._assert_otp_fallback(
            request=request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            destination="9876543210",
            resume_path="/accounts/register/",
        )

    def test_unverified_challenge_status_falls_back(self):
        issued = self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )
        request = self._request()
        self._seed_verified(request, challenge_id=issued.challenge.id)
        mock_issued = MagicMock()
        mock_issued.challenge_id = "fallback"
        mock_issued.flow_type = constants.FLOW_USER_REGISTRATION
        mock_issued.expires_at = datetime.now(timezone.utc)
        real = self.service

        class _Svc:
            def get_challenge_status(self, *, challenge_id):
                return real.get_challenge_status(challenge_id=challenge_id)

            def start_verification(self, **kwargs):
                return mock_issued

        with patch(
            "otp_verification.registration.gate.build_registration_otp_service",
            return_value=_Svc(),
        ):
            response = begin_otp_or_continue(
                request,
                flow_type=constants.FLOW_USER_REGISTRATION,
                destination="9876543210",
                payload={"email": "a@example.com", "password": "Secret123!"},
                resume_path="/accounts/register/",
                wants_json=True,
            )
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 202)
        status = real.get_challenge_status(challenge_id=issued.challenge.id)
        self.assertNotEqual(
            str(getattr(status.status, "value", status.status)),
            ChallengeStatus.VERIFIED.value,
        )

    def test_consume_clears_verified_and_challenge(self):
        request = self._request()
        issued = self._issue_and_verify()
        self._seed_verified(request, challenge_id=issued.challenge.id)
        self.assertIsNotNone(get_phone_verified(request))
        consume_phone_verified_session(request)
        self.assertIsNone(get_phone_verified(request, enforce_ttl=False))
        self.assertNotIn(PHONE_CHALLENGE_SESSION_KEY, request.session)
        self.assertNotIn(PHONE_VERIFIED_SESSION_KEY, request.session)

    def test_skip_does_not_consume_until_success_helper(self):
        """Gate skip keeps proof so failed registration can retry."""

        issued = self._issue_and_verify()
        request = self._request()
        self._seed_verified(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.gate.build_registration_otp_service",
            return_value=self.service,
        ):
            self.assertIsNone(
                begin_otp_or_continue(
                    request,
                    flow_type=constants.FLOW_USER_REGISTRATION,
                    destination="9876543210",
                    payload={"email": "a@example.com", "password": "Secret123!"},
                    resume_path="/accounts/register/",
                )
            )
        self.assertIsNotNone(get_phone_verified(request))
        # Simulate failed registration: do not consume; retry still skips OTP.
        with patch(
            "otp_verification.registration.gate.build_registration_otp_service",
            return_value=self.service,
        ):
            self.assertIsNone(
                begin_otp_or_continue(
                    request,
                    flow_type=constants.FLOW_USER_REGISTRATION,
                    destination="9876543210",
                    payload={"email": "a@example.com", "password": "Secret123!"},
                    resume_path="/accounts/register/",
                )
            )
        consume_phone_verified_session(request)
        self.assertIsNone(get_phone_verified(request, enforce_ttl=False))
