"""Unit tests for POST /otp/registration/send/ (Phase 3 Task 2 Part A)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.exceptions import (
    ProviderFailureException,
    ProviderTimeoutException,
)
from otp_verification.registration.contracts import RegistrationOTPIssueResult
from otp_verification.registration.gate import begin_otp_or_continue
from otp_verification.registration.exceptions import (
    RegistrationOTPDeliveryFailed,
    RegistrationOTPDisabled,
    RegistrationOTPRateLimited,
    RegistrationOTPValidationError,
)
from otp_verification.registration.factory import build_registration_otp_resend_service
from otp_verification.registration.responses import (
    ERROR_COOLDOWN,
    ERROR_DELIVERY_FAILED,
    ERROR_DISABLED,
    ERROR_GENERATION_LIMIT,
    ERROR_RATE_LIMITED,
    ERROR_VALIDATION,
)
from otp_verification.registration.session import (
    GENERATION_BUDGET_SESSION_KEY,
    PENDING_SESSION_KEY,
    PHONE_CHALLENGE_SESSION_KEY,
    get_otp_generation_count,
    get_phone_challenge,
    record_successful_otp_generation,
)
from otp_verification.registration.views import (
    send_registration_otp,
    verify_registration_otp,
)
from otp_verification.security.contracts import ReplayProtection
from otp_verification.services.factory import (
    build_otp_engine,
    build_otp_provider_runtime,
    reset_otp_process_storage,
)
from otp_verification.services.support import AuditLogger, NullLoggingBackend
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
        registration_pending_ttl_seconds=900,
        registration_completed_ttl_seconds=1800,
    )
    base.update(overrides)
    return OTPConfiguration(**base)


def _prepare_request(factory, *, data=None, content_type=None, body=None):
    if body is not None:
        request = factory.post(
            "/otp/registration/send/",
            data=body,
            content_type=content_type or "application/json",
        )
    else:
        request = factory.post("/otp/registration/send/", data=data or {})
    request.session = SessionStore()
    request.META["HTTP_ACCEPT"] = "application/json"
    return request


def _json(response):
    return json.loads(response.content.decode("utf-8"))


@override_settings(
    SECRET_KEY="test-secret-key-for-otp-send",
    OTP_CHALLENGE_STORAGE="memory",
    OTP_ENABLED=True,
    OTP_PROVIDER=constants.PROVIDER_MOCK_SMS,
)
class SendRegistrationOTPTests(SimpleTestCase):
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

    def tearDown(self):
        reset_otp_process_storage()

    def _patch_service(self):
        from otp_verification.registration.service import RegistrationOTPService

        return patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=RegistrationOTPService(
                runtime=self.runtime,
                configuration=self.config,
            ),
        )

    def test_successful_send_json_structure(self):
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        with self._patch_service():
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 200)
        body = _json(response)
        self.assertEqual(body["status"], "success")
        self.assertIn("challenge_id", body)
        self.assertEqual(body["flow_type"], constants.FLOW_USER_REGISTRATION)
        self.assertIn("expires_at", body)
        self.assertEqual(body["cooldown_remaining"], 60)
        self.assertIsNone(body.get("error_code"))
        self.assertIsInstance(body.get("result"), dict)
        self.assertEqual(body["result"]["challenge_id"], body["challenge_id"])
        self.assertEqual(body["result"]["cooldown_remaining"], 60)
        self.assertNotIn("otp", body)
        self.assertNotIn("otp_code", body)
        self.assertNotIn("otp_hash", body)
        self.assertNotIn(PENDING_SESSION_KEY, request.session)
        phone = get_phone_challenge(request)
        self.assertIsNotNone(phone)
        self.assertEqual(phone["challenge_id"], body["challenge_id"])
        self.assertEqual(phone["flow_type"], constants.FLOW_USER_REGISTRATION)
        self.assertEqual(phone["destination"], "919876543210")
        self.assertEqual(phone["resend_count"], 0)
        self.assertEqual(
            get_otp_generation_count(
                request, flow_type=constants.FLOW_USER_REGISTRATION
            ),
            1,
        )
        self.assertIn("created_at", phone)
        self.assertIn("last_resent_at", phone)
        self.assertNotIn("payload", phone)
        self.assertNotIn("password", phone)
        self.assertNotIn("email", phone)
        self.assertNotIn("resume_path", phone)

    def test_invalid_phone(self):
        request = _prepare_request(
            self.factory,
            data={"phone_number": "abc", "flow_type": constants.FLOW_USER_REGISTRATION},
        )
        with self._patch_service():
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 400)
        body = _json(response)
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["error"], ERROR_VALIDATION)

    def test_missing_phone(self):
        request = _prepare_request(
            self.factory,
            data={"flow_type": constants.FLOW_USER_REGISTRATION},
        )
        response = send_registration_otp(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(_json(response)["error"], ERROR_VALIDATION)

    def test_invalid_flow(self):
        request = _prepare_request(
            self.factory,
            data={"phone_number": "9876543210", "flow_type": "not_a_real_flow"},
        )
        with self._patch_service():
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(_json(response)["error"], ERROR_VALIDATION)

    def test_otp_disabled(self):
        disabled = _config(enabled=False)
        from otp_verification.registration.service import RegistrationOTPService

        runtime = build_otp_provider_runtime(
            configuration=disabled,
            engine=build_otp_engine(
                configuration=disabled,
                repository=InMemoryChallengeRepository(),
                replay_protector=ReplayProtection(),
                audit_logger=AuditLogger(backend=NullLoggingBackend()),
            ),
        )
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=RegistrationOTPService(runtime=runtime, configuration=disabled),
        ):
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(_json(response)["error"], ERROR_DISABLED)

    def test_provider_unavailable_maps_to_delivery_failed(self):
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        mock_service = MagicMock()
        mock_service.start_verification.side_effect = RegistrationOTPDeliveryFailed(
            "Unable to send verification code. Please try again later."
        )
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=mock_service,
        ):
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 502)
        body = _json(response)
        self.assertEqual(body["error"], ERROR_DELIVERY_FAILED)
        self.assertEqual(
            get_otp_generation_count(
                request, flow_type=constants.FLOW_USER_REGISTRATION
            ),
            0,
        )
        self.assertNotIn("traceback", body)
        self.assertNotIn("ProviderFailure", body.get("message", ""))

    def test_provider_timeout_via_service_mapping(self):
        """ProviderTimeoutException is mapped inside start_verification to delivery failed."""

        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_PANDIT_REGISTRATION,
            },
        )
        with self._patch_service(), patch.object(
            self.runtime.orchestrator,
            "deliver_otp",
            side_effect=ProviderTimeoutException("timeout"),
        ):
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(_json(response)["error"], ERROR_DELIVERY_FAILED)

    def test_rate_limited(self):
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        mock_service = MagicMock()
        mock_service.start_verification.side_effect = RegistrationOTPRateLimited(
            "Too many requests. Please try again later."
        )
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=mock_service,
        ):
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(_json(response)["error"], ERROR_RATE_LIMITED)

    def test_json_body_accepted(self):
        request = _prepare_request(
            self.factory,
            body=json.dumps(
                {
                    "phone_number": "9876543210",
                    "flow_type": constants.FLOW_BUREAU_REGISTRATION,
                }
            ),
            content_type="application/json",
        )
        with self._patch_service():
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(_json(response)["flow_type"], constants.FLOW_BUREAU_REGISTRATION)

    def test_audit_sanitization_no_otp_in_success_payload(self):
        issued = RegistrationOTPIssueResult(
            challenge_id="chal-1",
            flow_type=constants.FLOW_USER_REGISTRATION,
            status="VERIFY_PENDING",
            expires_at=datetime.now(timezone.utc),
            attempt_count=0,
            max_attempts=5,
        )
        mock_service = MagicMock()
        mock_service.start_verification.return_value = issued
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=mock_service,
        ):
            response = send_registration_otp(request)
        raw = response.content.decode("utf-8").lower()
        self.assertNotIn("otp_hash", raw)
        self.assertNotIn("auth_key", raw)
        self.assertNotIn('"otp":', raw)
        mock_service.start_verification.assert_called_once()
        kwargs = mock_service.start_verification.call_args.kwargs
        self.assertEqual(kwargs["destination"], "919876543210")
        self.assertEqual(kwargs["flow_type"], constants.FLOW_USER_REGISTRATION)
        self.assertNotIn("payload", kwargs)

    def test_does_not_create_pending_registration(self):
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        with self._patch_service():
            send_registration_otp(request)
        self.assertIn(PHONE_CHALLENGE_SESSION_KEY, request.session)
        self.assertNotIn(PENDING_SESSION_KEY, request.session)
        phone = request.session[PHONE_CHALLENGE_SESSION_KEY]
        self.assertNotIn("email", phone)
        self.assertNotIn("password", phone)
        self.assertNotIn("payload", phone)

    def test_second_click_during_cooldown_reuses_resend_policy(self):
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        with self._patch_service():
            first = send_registration_otp(request)
            self.assertEqual(first.status_code, 200)
            first_id = _json(first)["challenge_id"]
            second = send_registration_otp(request)
        self.assertEqual(second.status_code, 429)
        body = _json(second)
        self.assertEqual(body["error"], ERROR_COOLDOWN)
        self.assertGreater(body.get("remaining_seconds", 0), 0)
        # No uncontrolled second challenge while cooling down.
        self.assertEqual(
            request.session[PHONE_CHALLENGE_SESSION_KEY]["challenge_id"],
            first_id,
        )
        self.assertNotIn(PENDING_SESSION_KEY, request.session)

    def test_after_cooldown_uses_existing_resend_path(self):
        config = _config(resend_cooldown_seconds=0, max_resends=3)
        from otp_verification.registration.service import RegistrationOTPService

        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        service = RegistrationOTPService(runtime=runtime, configuration=config)
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=service,
        ), patch(
            "otp_verification.registration.views.build_registration_otp_resend_service",
            return_value=build_registration_otp_resend_service(
                runtime=runtime,
                configuration=config,
            ),
        ):
            first = send_registration_otp(request)
            self.assertEqual(first.status_code, 200)
            first_id = _json(first)["challenge_id"]
            second = send_registration_otp(request)
        self.assertEqual(second.status_code, 200)
        second_body = _json(second)
        self.assertNotEqual(second_body["challenge_id"], first_id)
        self.assertEqual(
            request.session[PHONE_CHALLENGE_SESSION_KEY]["challenge_id"],
            second_body["challenge_id"],
        )
        self.assertEqual(request.session[PHONE_CHALLENGE_SESSION_KEY]["resend_count"], 1)
        self.assertEqual(
            get_otp_generation_count(
                request, flow_type=constants.FLOW_USER_REGISTRATION
            ),
            2,
        )
        self.assertNotIn(PENDING_SESSION_KEY, request.session)

    def test_five_generations_allowed_and_sixth_blocked_via_send_endpoint(self):
        config = _config(resend_cooldown_seconds=0, max_resends=1)
        from otp_verification.registration.service import RegistrationOTPService

        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        service = RegistrationOTPService(runtime=runtime, configuration=config)
        resend = build_registration_otp_resend_service(
            runtime=runtime,
            configuration=config,
        )
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=service,
        ), patch(
            "otp_verification.registration.views.build_registration_otp_resend_service",
            return_value=resend,
        ):
            for expected_count in range(1, 6):
                response = send_registration_otp(request)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    get_otp_generation_count(
                        request, flow_type=constants.FLOW_USER_REGISTRATION
                    ),
                    expected_count,
                )
            limited = send_registration_otp(request)
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(_json(limited)["error"], ERROR_GENERATION_LIMIT)
        self.assertEqual(
            len(runtime.engine.repository._records),
            constants.MAX_OTP_GENERATIONS_PER_SESSION,
        )

    def test_fifth_generation_remains_verifiable(self):
        config = _config(resend_cooldown_seconds=0, max_resends=1)
        from otp_verification.registration.service import RegistrationOTPService

        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
            audit_logger=AuditLogger(backend=NullLoggingBackend()),
        )
        runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        service = RegistrationOTPService(runtime=runtime, configuration=config)
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=service,
        ), patch(
            "otp_verification.registration.views.build_registration_otp_resend_service",
            return_value=build_registration_otp_resend_service(
                runtime=runtime,
                configuration=config,
            ),
        ):
            responses = [send_registration_otp(request) for _ in range(5)]
            blocked = send_registration_otp(request)

        fifth_challenge = _json(responses[-1])["challenge_id"]
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(_json(blocked)["error"], ERROR_GENERATION_LIMIT)
        verified = MagicMock(
            challenge_id=fifth_challenge,
            flow_type=constants.FLOW_USER_REGISTRATION,
        )
        verify_service = MagicMock()
        verify_service.verify_challenge.return_value = verified
        verify_request = self.factory.post(
            "/otp/registration/verify/",
            data={"challenge_id": fifth_challenge, "otp": "123456"},
        )
        verify_request.session = request.session
        verify_request.META["HTTP_ACCEPT"] = "application/json"
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=verify_service,
        ):
            response = verify_registration_otp(verify_request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(_json(response)["result"]["phone_verified"])
        self.assertEqual(
            get_otp_generation_count(
                verify_request, flow_type=constants.FLOW_USER_REGISTRATION
            ),
            5,
        )
        verify_service.verify_challenge.assert_called_once_with(
            challenge_id=fifth_challenge,
            submitted_otp="123456",
        )

    def test_referral_resubmission_does_not_reset_generation_budget(self):
        request = _prepare_request(self.factory, data={})
        issues = [
            RegistrationOTPIssueResult(
                challenge_id=f"referral-{index}",
                flow_type=constants.FLOW_PANDIT_REGISTRATION,
                status="VERIFY_PENDING",
                expires_at=datetime.now(timezone.utc),
                attempt_count=0,
                max_attempts=5,
            )
            for index in range(1, 6)
        ]
        service = MagicMock()
        service.start_verification.side_effect = issues
        with patch(
            "otp_verification.registration.gate.is_registration_otp_required",
            return_value=True,
        ), patch(
            "otp_verification.registration.gate.build_registration_otp_service",
            return_value=service,
        ):
            for expected_count in range(1, 6):
                response = begin_otp_or_continue(
                    request,
                    flow_type=constants.FLOW_PANDIT_REGISTRATION,
                    destination="919876543210",
                    payload={
                        "email": "pandit@example.com",
                        "password": "Secret123!",
                        "referral_code": "SAME-REFERRAL",
                    },
                    resume_path="/accounts/pandit/register/",
                    wants_json=True,
                )
                self.assertEqual(response.status_code, 202)
                self.assertEqual(
                    get_otp_generation_count(
                        request, flow_type=constants.FLOW_PANDIT_REGISTRATION
                    ),
                    expected_count,
                )
            blocked = begin_otp_or_continue(
                request,
                flow_type=constants.FLOW_PANDIT_REGISTRATION,
                destination="919876543210",
                payload={
                    "email": "pandit@example.com",
                    "password": "Secret123!",
                    "referral_code": "SAME-REFERRAL",
                },
                resume_path="/accounts/pandit/register/",
                wants_json=True,
            )

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(_json(blocked)["error"], ERROR_GENERATION_LIMIT)
        self.assertEqual(service.start_verification.call_count, 5)
        self.assertIn(GENERATION_BUDGET_SESSION_KEY, request.session)

    def test_authenticated_edit_profile_budget_follows_django_session(self):
        user = SimpleNamespace(is_authenticated=True, pk=42)
        shared_session = SessionStore()
        first_request = _prepare_request(self.factory, data={})
        first_request.session = shared_session
        record_successful_otp_generation(
            first_request, flow_type=constants.FLOW_USER_REGISTRATION
        )

        # Registration can begin anonymously; logging in later within the same
        # Django session must not create a fresh Edit Profile verification budget.
        later_request = _prepare_request(self.factory, data={})
        later_request.session = shared_session
        later_request.user = user
        self.assertEqual(
            get_otp_generation_count(
                later_request, flow_type=constants.FLOW_USER_REGISTRATION
            ),
            1,
        )

        new_session_request = _prepare_request(self.factory, data={})
        new_session_request.user = user
        self.assertEqual(
            get_otp_generation_count(
                new_session_request, flow_type=constants.FLOW_USER_REGISTRATION
            ),
            0,
        )

    def test_rapid_repeated_clicks_do_not_create_uncontrolled_challenges(self):
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        with self._patch_service():
            first = send_registration_otp(request)
            challenge_id = _json(first)["challenge_id"]
            statuses = []
            for _ in range(4):
                response = send_registration_otp(request)
                statuses.append(response.status_code)
                # Challenge id must remain the first one while cooldown blocks.
                self.assertEqual(
                    request.session[PHONE_CHALLENGE_SESSION_KEY]["challenge_id"],
                    challenge_id,
                )
        self.assertTrue(all(status == 429 for status in statuses))
        self.assertEqual(len(self.runtime.engine.repository._records), 1)

    def test_challenge_replacement_on_different_phone(self):
        shared = SessionStore()
        request_a = self.factory.post(
            "/otp/registration/send/",
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        request_a.session = shared
        request_a.META["HTTP_ACCEPT"] = "application/json"
        request_b = self.factory.post(
            "/otp/registration/send/",
            data={
                "phone_number": "9123456780",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        request_b.session = shared
        request_b.META["HTTP_ACCEPT"] = "application/json"
        with self._patch_service():
            first = send_registration_otp(request_a)
            first_id = _json(first)["challenge_id"]
            second = send_registration_otp(request_b)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        second_id = _json(second)["challenge_id"]
        self.assertNotEqual(first_id, second_id)
        phone = get_phone_challenge(request_b)
        self.assertEqual(phone["challenge_id"], second_id)
        self.assertEqual(phone["destination"], "919123456780")
        self.assertEqual(phone["resend_count"], 0)
        self.assertEqual(
            get_otp_generation_count(
                request_b, flow_type=constants.FLOW_USER_REGISTRATION
            ),
            2,
        )
        self.assertIn(GENERATION_BUDGET_SESSION_KEY, shared)
        self.assertNotIn(PENDING_SESSION_KEY, shared)

    def test_discards_empty_pending_bridge_on_send(self):
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        request.session[PENDING_SESSION_KEY] = {
            "flow_type": constants.FLOW_USER_REGISTRATION,
            "challenge_id": "old-bridge",
            "destination": "9876543210",
            "payload": {},
            "resume_path": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resend_count": 0,
            "last_resent_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._patch_service():
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(PENDING_SESSION_KEY, request.session)
        self.assertIsNotNone(get_phone_challenge(request))

    def test_preserves_real_pending_registration_on_send(self):
        request = _prepare_request(
            self.factory,
            data={
                "phone_number": "9876543210",
                "flow_type": constants.FLOW_USER_REGISTRATION,
            },
        )
        request.session[PENDING_SESSION_KEY] = {
            "flow_type": constants.FLOW_USER_REGISTRATION,
            "challenge_id": "real-pending",
            "destination": "9876543210",
            "payload": {"email": "user@example.com"},
            "resume_path": "/register/",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resend_count": 0,
            "last_resent_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._patch_service():
            response = send_registration_otp(request)
        self.assertEqual(response.status_code, 200)
        pending = request.session.get(PENDING_SESSION_KEY)
        self.assertIsInstance(pending, dict)
        self.assertEqual(pending.get("challenge_id"), "real-pending")
        self.assertEqual((pending.get("payload") or {}).get("email"), "user@example.com")
        self.assertIsNotNone(get_phone_challenge(request))
