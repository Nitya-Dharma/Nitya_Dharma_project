# OTP Verification Foundation

This package is the Phase 2 foundation for a future pre-registration SMS OTP
subsystem.

- Task 1: architecture, contracts, configuration
- Task 2: internal OTP engine
- Task 3: mock provider abstraction + orchestration
- Task 4: MSG91 SMS Flow provider (delivery only)

## Architecture Overview

```text
ChallengeManager (engine)
  → generate + hash + store hash
  → ChallengeIssueResult(otp_code transient)
ProviderOrchestrator
  → ProviderRequest(message=otp_code)
ProviderResolver / Registry / Factory
  → MockOTPProvider | Msg91SmsProvider
RequestsHttpTransport (HTTPS JSON POST)
  → MSG91 SMS Flow API v5
ProviderResponse → ProviderResult
```

OTP generation, hashing, verification, expiry, replay, and lockout remain
inside the OTP Engine. MSG91 only delivers SMS.

## Providers

### MockOTPProvider
Deterministic local simulation. No network.

### Msg91SmsProvider
Production delivery via MSG91 **SMS Flow API v5** only.

- Does **not** call MSG91 VerifyOTP / ResendOTP / Widget / legacy sendotp.php
- Maps `ProviderRequest.message` into configured template variable
- Uses reusable `RequestsHttpTransport`

## Configuration / Environment Variables

```text
OTP_ENABLED=false|true
OTP_CHALLENGE_STORAGE=database|memory   # default database (Task 8 multi-worker)
OTP_PROVIDER=mock_sms|msg91
OTP_PROVIDER_ENABLED=true
OTP_PROVIDER_AUDIT_ENABLED=true
OTP_PROVIDER_METRICS_ENABLED=true
OTP_REGISTRATION_PENDING_TTL_SECONDS=900    # default 15 minutes
OTP_REGISTRATION_COMPLETED_TTL_SECONDS=1800 # default 30 minutes
OTP_RESEND_COOLDOWN_SECONDS=60              # settings default; use 30 for tighter UX
OTP_MAX_RESENDS=3                           # successful resends per pending registration

# MSG91 (required when OTP_PROVIDER=msg91)
MSG91_AUTH_KEY=...
MSG91_BASE_URL=https://control.msg91.com/api/v5/flow/
MSG91_FLOW_ID=...
MSG91_SENDER_ID=...
MSG91_TEMPLATE_VARIABLE=OTP
MSG91_COUNTRY_CODE=91
MSG91_TIMEOUT_SECONDS=10
```

Switching providers requires **configuration only**.

## Challenge Storage (Task 8)

```text
ChallengeManager
  → BaseChallengeRepository
       ├── DjangoChallengeRepository  (OTP_CHALLENGE_STORAGE=database, default)
       └── InMemoryChallengeRepository (memory / tests / emergency rollback)
  → BaseReplayProtector
       ├── DatabaseReplayProtection
       └── ReplayProtection (process-local)
```

- Default **`database`** persists challenges + replay tokens in the app DB (multi-worker / restart safe).
- Apply migration: `python manage.py migrate otp_verification`
- Rollback storage without code change: `OTP_CHALLENGE_STORAGE=memory` (single-worker only).
- Services never import a concrete repository; factory DI selects the backend.
- Background purge of expired rows is **deferred** (lazy expiry on access remains).

Architecture review: `otp_verification_phase2_task8_part8a_report.md`  
Implementation: `otp_verification_phase2_task8_part8b_report.md`  
Production readiness: `otp_verification_phase2_task8_final_production_readiness_report.md`
## Security

- HTTPS enforced by transport
- Auth key only in HTTP header; never audited/logged
- OTP only in transient handoff / outbound payload
- Audit strips otp/message/headers/auth/flow/sender/payloads
- Repository stores hash only

## Transport Layer

`otp_verification.transport.RequestsHttpTransport`

- Single HTTP library: `requests`
- JSON POST
- Timeout support
- Transport exception translation
- Retry disabled

## Testing

```bash
python manage.py test otp_verification.tests.unit
```

All MSG91 tests mock HTTP. No real SMS is sent.

## Adding a Future Provider

1. Implement `BaseOTPProvider`
2. Add config values
3. Register a `ProviderDescriptor`
4. Resolve via existing factory/resolver

No OTP engine changes required.

## Registration Integration (Task 5)

Registration modules must use **only**:

```python
from otp_verification.registration import (
    build_registration_otp_service,
    is_registration_otp_required,
)
```

- Default: `OTP_ENABLED=false` — registration behaves exactly as before.
- When enabled: validation → issue OTP → pause (session pending) → verify at `/otp/registration/verify/` → complete registration.
- Registration never imports MSG91, transport, registry, or provider DTOs.
- Verify requires session-owned challenge ID (no challenge swapping).
- Pending session stores allowlisted fields only; passwords stored as hashes.
- Double verify / refresh is idempotent via completed-session marker.
- Pending registration sessions expire after `OTP_REGISTRATION_PENDING_TTL_SECONDS` (default 900s).
- Registration finalization uses session `completed` marker (engine stays `VERIFIED`; ChallengeManager public API unchanged).
- JSON clients should send `Accept: application/json` (and CSRF token for cookie sessions).
- **Resend:** `POST /otp/registration/resend/` creates a **new** challenge via existing `deliver_otp`, rebinds pending or phone-challenge `challenge_id`, enforces cooldown + max resends (Task 7).
- **Send (lightweight, Task 2 Part A / A.1 / B):** `POST /otp/registration/send/` — JSON adapter. First matching request uses `RegistrationOTPService.start_verification` and stores **`otp.registration.phone_challenge`** only (`challenge_id`, `flow_type`, `destination`, `created_at`, `last_resent_at`, `resend_count`). Subsequent matching requests reuse **existing** `RegistrationOTPResendService` against that session (cooldown, limits, ownership, eligibility). Does **not** create `otp.registration.pending` and does **not** store registration form payload. CSRF + POST required.
- **Session separation:** `otp.registration.pending` remains for paused registration after form submit. Pre-registration phone verification uses **`otp.registration.phone_challenge`** only (empty-pending bridge retired).
- **Phone verified (Task 2 Part C / D):** After successful OTP verify (including phone_challenge-only verify), session key **`otp.registration.phone_verified`** stores temporary proof: `challenge_id`, `destination`, `flow_type`, `verified_at`, `expires_at`. Expiry reuses `OTP_REGISTRATION_PENDING_TTL_SECONDS`. Cleared on expiry, new phone challenge / challenge rebind, or explicit cleanup.
- **Registration consume (Part D):** `begin_otp_or_continue` validates phone_verified (destination + flow + non-expired + challenge still `VERIFIED`). If valid, returns `None` so the **existing** registration create path runs (no second OTP). Invalid/missing proof falls back to normal OTP issue. Proof is consumed via `consume_phone_verified_session` only after successful account creation (kept on validation/DB failure for retry).
- **Reusable mobile verification UI (Phase 3 Task 2–5 / 6.1):** Partial `templates/otp_verification/partials/mobile_verification.html` on User / Pandit / Expert / Bureau registration. Shared client module `static/js/mobile_verification.js` initializes each `[data-nd-mobile-verification]` from `data-*` and calls existing `/otp/registration/send|verify|resend/` endpoints. Verify success trusts only `result.phone_verified === true`. Partial renders **only** when existing `is_registration_otp_required(flow_type)` is true (via `registration_otp_required` template tag); when OTP is off the widget is omitted so Register behaves as before. Presentation polish via Bootstrap classes + `static/css/mobile_verification.css`. Client UX only when OTP is on; server `phone_verified` remains authoritative.
- Lifecycle hardening details: `otp_verification_phase2_task6_part6b_report.md`
- Resend design: `otp_verification_phase2_task7_part7a_report.md`

## Known Limitations

- Redis challenge repository not implemented (DB is the durable default; Redis is a future option)
- No automated background purge of expired challenge rows (lazy expiry on access; purge deferred)
- No Redis-backed resend cooldown (session-scoped)
- No delivery webhooks/reports
- No analytics / admin OTP dashboard
- MSG91 DLT template approval is an account prerequisite
- Legacy `become_expert_home` path is not OTP-gated
- Engine `VERIFIED → CONSUMED` not written (replay already terminal; see Part 6B report)
- Hardening details: `otp_verification_phase2_task5_hardening_report.md`
- Production QA: `otp_verification_phase2_task6_production_qa_report.md`
- Resend reports: `otp_verification_phase2_task7_part7b_report.md`
- Durable storage: `otp_verification_phase2_task8_part8a_report.md`, `otp_verification_phase2_task8_part8b_report.md`