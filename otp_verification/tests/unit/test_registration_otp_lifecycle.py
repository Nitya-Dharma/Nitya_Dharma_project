"""Phase 2 Task 6 Part 6B — verification lifecycle hardening tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from otp_verification import constants
from otp_verification.config import OTPConfiguration
from otp_verification.enums import SimulationMode
from otp_verification.exceptions import ReplayAttackException
from otp_verification.registration.adapters import map_exception
from otp_verification.registration.completions import CompletionError
from otp_verification.registration.exceptions import (
    RegistrationOTPReplay,
    RegistrationOTPSessionExpired,
)
from otp_verification.registration.factory import build_registration_otp_service
from otp_verification.registration.responses import (
    ERROR_EXPIRED_CHALLENGE,
    ERROR_LOCKED_CHALLENGE,
    ERROR_OWNERSHIP,
    ERROR_REPLAY,
    ERROR_SESSION_EXPIRED,
    ERROR_UNEXPECTED,
    ERROR_VALIDATION,
)
from otp_verification.registration.session import (
    PENDING_SESSION_KEY,
    clear_pending_registration,
    finalize_registration_session,
    get_completed_registration,
    get_pending_registration,
    is_registration_otp_verified,
    mark_registration_otp_verified,
    store_pending_registration,
)
from otp_verification.registration.views import verify_registration_otp
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


def _prepare_request(
    factory: RequestFactory,
    method="get",
    path="/otp/registration/verify/",
    data=None,
):
    if method == "post":
        request = factory.post(path, data=data or {})
    else:
        request = factory.get(path)
    request.session = SessionStore()
    request._messages = FallbackStorage(request)
    return request


def _as_json_client(request) -> None:
    """Ask the verify view for JSON envelopes without altering content_type."""

    request.META["HTTP_ACCEPT"] = "application/json"


def _json_body(response) -> dict:
    return json.loads(response.content.decode("utf-8"))


@override_settings(
    SECRET_KEY="test-secret-key-for-registration-lifecycle",
    OTP_ENABLED=True,
    OTP_PROVIDER=constants.PROVIDER_MOCK_SMS,
    OTP_REGISTRATION_PENDING_TTL_SECONDS=900,
    OTP_REGISTRATION_COMPLETED_TTL_SECONDS=1800,
)
class RegistrationOTPLifecycleHardeningTests(SimpleTestCase):
    def setUp(self):
        reset_otp_process_storage()
        self.factory = RequestFactory()
        config = _config(max_attempts=3)
        engine = build_otp_engine(
            configuration=config,
            repository=InMemoryChallengeRepository(),
            replay_protector=ReplayProtection(),
        )
        self.runtime = build_otp_provider_runtime(configuration=config, engine=engine)
        self.service = build_registration_otp_service(runtime=self.runtime)

    def _issue(self):
        return self.runtime.engine.challenge_manager.create_challenge(
            flow_type=constants.FLOW_USER_REGISTRATION,
            context={},
        )

    def _store_pending(self, request, *, challenge_id: str, email: str = "life@example.com"):
        store_pending_registration(
            request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            challenge_id=challenge_id,
            destination="9876543210",
            payload={"email": email, "password": "Secret123!"},
            resume_path="/accounts/register/",
        )

    def test_pending_stores_created_at(self):
        request = _prepare_request(self.factory)
        self._store_pending(request, challenge_id="c-ttl")
        pending = get_pending_registration(request)
        self.assertIsNotNone(pending)
        self.assertIn("created_at", pending)

    def test_expired_pending_session_clears_and_raises(self):
        request = _prepare_request(self.factory)
        self._store_pending(request, challenge_id="c-old")
        pending = request.session[PENDING_SESSION_KEY]
        pending["created_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        request.session[PENDING_SESSION_KEY] = pending
        request.session.modified = True

        with self.assertRaises(RegistrationOTPSessionExpired):
            get_pending_registration(request, enforce_ttl=True)
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))

    def test_verify_expired_session_json(self):
        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": "c-old", "otp": "123456"},
        )
        _as_json_client(request)
        self._store_pending(request, challenge_id="c-old", email="old2@example.com")
        pending = request.session[PENDING_SESSION_KEY]
        pending["created_at"] = (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).isoformat()
        request.session[PENDING_SESSION_KEY] = pending

        response = verify_registration_otp(request)
        self.assertEqual(response.status_code, 400)
        body = _json_body(response)
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["error"], ERROR_SESSION_EXPIRED)

    def test_ownership_failure_json_clears_pending(self):
        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": "forged", "otp": "123456"},
        )
        _as_json_client(request)
        self._store_pending(request, challenge_id="real-challenge", email="own@example.com")
        response = verify_registration_otp(request)
        body = _json_body(response)
        self.assertEqual(body["error"], ERROR_OWNERSHIP)
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))

    def test_empty_otp_validation_error_keeps_pending(self):
        issued = self._issue()
        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": issued.challenge.id, "otp": ""},
        )
        _as_json_client(request)
        self._store_pending(request, challenge_id=issued.challenge.id, email="val@example.com")
        response = verify_registration_otp(request)
        body = _json_body(response)
        self.assertEqual(body["error"], ERROR_VALIDATION)
        self.assertIsNotNone(get_pending_registration(request))

    def test_expired_challenge_clears_pending(self):
        issued = self._issue()
        record = self.runtime.engine.challenge_manager.repository.get_by_id(
            issued.challenge.id
        )
        expired_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        updated = record.copy_with(expires_at=expired_at, updated_at=expired_at)
        self.runtime.engine.challenge_manager.repository.update(
            issued.challenge.id, payload={"record": updated}
        )

        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": issued.challenge.id, "otp": "123456"},
        )
        _as_json_client(request)
        self._store_pending(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = _json_body(response)
        self.assertEqual(body["error"], ERROR_EXPIRED_CHALLENGE)
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))

    def test_locked_challenge_clears_pending(self):
        issued = self._issue()
        for _ in range(3):
            try:
                self.service.verify_challenge(
                    challenge_id=issued.challenge.id, submitted_otp="000000"
                )
            except Exception:
                pass

        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": issued.challenge.id, "otp": "000000"},
        )
        _as_json_client(request)
        self._store_pending(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = _json_body(response)
        self.assertEqual(body["error"], ERROR_LOCKED_CHALLENGE)
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))

    def test_replay_maps_and_clears_pending(self):
        mapped = map_exception(ReplayAttackException("replay"))
        self.assertIsInstance(mapped, RegistrationOTPReplay)

        issued = self._issue()
        otp = issued.otp_code
        self.service.verify_challenge(challenge_id=issued.challenge.id, submitted_otp=otp)

        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": issued.challenge.id, "otp": otp},
        )
        _as_json_client(request)
        self._store_pending(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.build_registration_otp_service",
            return_value=self.service,
        ):
            response = verify_registration_otp(request)
        body = _json_body(response)
        self.assertEqual(body["error"], ERROR_REPLAY)
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))

    def test_finalize_clears_pending_keeps_completed(self):
        request = _prepare_request(self.factory)
        self._store_pending(request, challenge_id="fin-1", email="fin@example.com")
        mark_registration_otp_verified(
            request,
            challenge_id="fin-1",
            flow_type=constants.FLOW_USER_REGISTRATION,
        )
        finalize_registration_session(
            request,
            challenge_id="fin-1",
            flow_type=constants.FLOW_USER_REGISTRATION,
            result={"flow_type": constants.FLOW_USER_REGISTRATION, "user_id": 9},
        )
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))
        self.assertFalse(
            is_registration_otp_verified(
                request,
                flow_type=constants.FLOW_USER_REGISTRATION,
                challenge_id="fin-1",
            )
        )
        completed = get_completed_registration(request)
        self.assertEqual(completed["challenge_id"], "fin-1")

    def test_duplicate_post_idempotent_after_finalize(self):
        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": "done-2", "otp": "ignored"},
        )
        _as_json_client(request)
        finalize_registration_session(
            request,
            challenge_id="done-2",
            flow_type=constants.FLOW_USER_REGISTRATION,
            result={"flow_type": constants.FLOW_USER_REGISTRATION, "user_id": 2},
        )
        clear_pending_registration(request)
        response = verify_registration_otp(request)
        self.assertEqual(response.status_code, 200)
        body = _json_body(response)
        self.assertEqual(body["status"], "success")

    def test_browser_refresh_get_with_pending(self):
        issued = self._issue()
        request = _prepare_request(self.factory)
        self._store_pending(request, challenge_id=issued.challenge.id)
        with patch(
            "otp_verification.registration.views.render",
            return_value=HttpResponse("ok"),
        ) as mock_render:
            response = verify_registration_otp(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_render.called)
        self.assertEqual(
            mock_render.call_args.args[2]["challenge_id"],
            issued.challenge.id,
        )

    def test_completion_error_keeps_verified_pending(self):
        issued = self._issue()
        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": issued.challenge.id, "otp": "ignored"},
        )
        _as_json_client(request)
        self._store_pending(request, challenge_id=issued.challenge.id)
        mark_registration_otp_verified(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_USER_REGISTRATION,
        )

        with patch(
            "otp_verification.registration.views.complete_pending_registration",
            side_effect=CompletionError("db failed"),
        ):
            response = verify_registration_otp(request)
        body = _json_body(response)
        self.assertEqual(body["error"], "registration_failed")
        self.assertIsNotNone(get_pending_registration(request))
        self.assertTrue(
            is_registration_otp_verified(
                request,
                flow_type=constants.FLOW_USER_REGISTRATION,
                challenge_id=issued.challenge.id,
            )
        )

    def test_unexpected_exception_does_not_leak_and_keeps_pending(self):
        issued = self._issue()
        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": issued.challenge.id, "otp": "ignored"},
        )
        _as_json_client(request)
        self._store_pending(request, challenge_id=issued.challenge.id)
        mark_registration_otp_verified(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_USER_REGISTRATION,
        )

        with patch(
            "otp_verification.registration.views.complete_pending_registration",
            side_effect=RuntimeError("secret provider stack"),
        ):
            response = verify_registration_otp(request)
        body = _json_body(response)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"], ERROR_UNEXPECTED)
        self.assertNotIn("secret provider", body["message"])
        self.assertIsNotNone(get_pending_registration(request))

    def test_legacy_pending_without_created_at_treated_expired(self):
        request = _prepare_request(self.factory)
        request.session[PENDING_SESSION_KEY] = {
            "flow_type": constants.FLOW_USER_REGISTRATION,
            "challenge_id": "legacy",
            "destination": "9876543210",
            "payload": {},
            "resume_path": "/accounts/register/",
        }
        with self.assertRaises(RegistrationOTPSessionExpired):
            get_pending_registration(request)

    def test_verified_gate_redirects_instead_of_legacy_fallthrough(self):
        from otp_verification.registration.gate import begin_otp_or_continue

        request = _prepare_request(self.factory, method="post", data={})
        store_pending_registration(
            request,
            flow_type=constants.FLOW_USER_REGISTRATION,
            challenge_id="gate-1",
            destination="9876543210",
            payload={"email": "gate@example.com", "password": "Secret123!"},
            resume_path="/accounts/register/",
        )
        mark_registration_otp_verified(
            request,
            challenge_id="gate-1",
            flow_type=constants.FLOW_USER_REGISTRATION,
        )
        with override_settings(OTP_ENABLED=True, ROOT_URLCONF="nityadharma.urls"):
            response = begin_otp_or_continue(
                request,
                flow_type=constants.FLOW_USER_REGISTRATION,
                destination="9876543210",
                payload={"email": "tampered@example.com", "password": "Other!"},
                resume_path="/accounts/register/",
            )
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/otp/registration/verify/", response.url)

    def test_concurrent_verified_resume_skips_reverify(self):
        """Second POST after verified marker resumes completion without re-OTP."""

        issued = self._issue()
        request = _prepare_request(
            self.factory,
            method="post",
            data={"challenge_id": issued.challenge.id, "otp": "should-be-ignored"},
        )
        _as_json_client(request)
        self._store_pending(request, challenge_id=issued.challenge.id)
        mark_registration_otp_verified(
            request,
            challenge_id=issued.challenge.id,
            flow_type=constants.FLOW_USER_REGISTRATION,
        )
        with patch(
            "otp_verification.registration.views.complete_pending_registration",
            return_value={
                "flow_type": constants.FLOW_USER_REGISTRATION,
                "user_id": 42,
                "email": "life@example.com",
            },
        ) as complete:
            response = verify_registration_otp(request)
        self.assertTrue(complete.called)
        body = _json_body(response)
        self.assertEqual(body["status"], "success")
        self.assertIsNone(get_pending_registration(request, enforce_ttl=False))
