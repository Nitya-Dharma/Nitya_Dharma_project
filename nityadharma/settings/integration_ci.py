"""
Fail-closed GitHub Actions integration-CI settings for ZeptoMail email QA.

Selection (explicit only — never the default):
  DJANGO_SETTINGS_MODULE=nityadharma.settings.integration_ci

Safety properties:
- Imports nityadharma.settings.qa first (fail-closed MySQL host/name guards,
  rejects DATABASE_URL/MYSQL_URL, empty ZeptoMail allowlist, LocMem cache).
- Disables Celery eager mode and requires a disposable Redis broker whose
  hostname exactly matches INTEGRATION_CI_ALLOWED_REDIS_HOSTS.
- Forces the CI-only recording file email backend (no SMTP / Resend / ZeptoMail).
- Constrains EMAIL_FILE_PATH to a dedicated /tmp directory (no traversal).
- Does not alter base.py / prod.py / dev.py / qa.py or Celery task routes.

Do not point these settings at development or production databases or Redis.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

from .qa import *  # noqa: F401,F403
from .qa import _is_forbidden_qa_host  # reuse qa fail-closed host forms


def _env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(
            f"integration_ci settings require process env {name}=… "
            f"(no default; .env is not consulted for this key)."
        )
    return value


def _env_optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _require_ci_test_recipient(address: str, *, label: str) -> str:
    addr = (address or "").strip().lower()
    if not addr or "@" not in addr:
        raise ImproperlyConfigured(f"{label} must be a non-empty email address.")
    if not (addr.endswith(".invalid") or addr.endswith(".test")):
        raise ImproperlyConfigured(
            f"{label}={address!r} must use a .invalid or .test address in CI."
        )
    return address.strip()


def _resolve_email_file_path(raw: str) -> str:
    """
    Force EMAIL_FILE_PATH under the dedicated CI temp root.

    Rejects relative paths, `..` segments, and symlink escapes that resolve
    outside the allowlisted root.
    """
    allowed_root = Path("/tmp/nitya-dharma-integration-mail")
    raw_path = Path(raw)
    if not raw_path.is_absolute():
        raise ImproperlyConfigured(
            "INTEGRATION_CI_EMAIL_FILE_PATH must be an absolute path under "
            f"{allowed_root}."
        )
    if ".." in raw_path.parts:
        raise ImproperlyConfigured(
            "INTEGRATION_CI_EMAIL_FILE_PATH must not contain '..' segments."
        )

    # Materialize the allowlisted root as a real directory (not a symlink).
    allowed_root.mkdir(parents=True, exist_ok=True)
    if allowed_root.is_symlink():
        raise ImproperlyConfigured(
            f"CI email root {allowed_root} must not be a symbolic link."
        )
    allowed_resolved = allowed_root.resolve()
    if not str(allowed_resolved).startswith("/tmp/"):
        raise ImproperlyConfigured(
            f"CI email root resolved outside /tmp: {allowed_resolved}"
        )

    candidate = raw_path
    # Create leaf directory when missing so resolve() can validate placement.
    candidate.mkdir(parents=True, exist_ok=True)
    if candidate.is_symlink():
        raise ImproperlyConfigured(
            f"INTEGRATION_CI_EMAIL_FILE_PATH {raw!r} must not be a symbolic link."
        )
    resolved = candidate.resolve()
    try:
        resolved.relative_to(allowed_resolved)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"INTEGRATION_CI_EMAIL_FILE_PATH={raw!r} resolves to {resolved} "
            f"which is outside the dedicated CI directory {allowed_resolved}."
        ) from exc
    return str(resolved)


# ---------------------------------------------------------------------------
# Redis broker — disposable hostname allowlist (fail-closed)
# ---------------------------------------------------------------------------

_raw_allowed_redis = _env_required("INTEGRATION_CI_ALLOWED_REDIS_HOSTS")
_allowed_redis_hosts: list[str] = []
for _entry in _raw_allowed_redis.split(","):
    _candidate = _entry.strip()
    if not _candidate:
        continue
    if _is_forbidden_qa_host(_candidate):
        raise ImproperlyConfigured(
            "INTEGRATION_CI_ALLOWED_REDIS_HOSTS contains a forbidden host form "
            f"({_candidate!r}). Localhost / loopback / wildcard are never permitted."
        )
    _allowed_redis_hosts.append(_candidate)

if not _allowed_redis_hosts:
    raise ImproperlyConfigured(
        "INTEGRATION_CI_ALLOWED_REDIS_HOSTS must list at least one approved "
        "disposable Redis hostname (e.g. the GitHub Actions service alias redis)."
    )

_broker_url = _env_required("INTEGRATION_CI_REDIS_URL")
_parsed_broker = urlparse(_broker_url)
if _parsed_broker.scheme not in {"redis", "rediss"}:
    raise ImproperlyConfigured(
        "INTEGRATION_CI_REDIS_URL must use redis:// or rediss:// "
        f"(got scheme={_parsed_broker.scheme!r})."
    )
_broker_host = (_parsed_broker.hostname or "").strip()
if _is_forbidden_qa_host(_broker_host):
    raise ImproperlyConfigured(
        f"INTEGRATION_CI_REDIS_URL host {_broker_host!r} is forbidden."
    )
if _broker_host not in _allowed_redis_hosts:
    raise ImproperlyConfigured(
        f"INTEGRATION_CI_REDIS_URL host {_broker_host!r} is not in "
        "INTEGRATION_CI_ALLOWED_REDIS_HOSTS."
    )

# Optional result backend; default to same disposable Redis URL.
_result_url = _env_optional("INTEGRATION_CI_REDIS_RESULT_URL", _broker_url)
_parsed_result = urlparse(_result_url)
_result_host = (_parsed_result.hostname or "").strip()
if _parsed_result.scheme not in {"redis", "rediss"}:
    raise ImproperlyConfigured(
        "INTEGRATION_CI_REDIS_RESULT_URL must use redis:// or rediss://."
    )
if _is_forbidden_qa_host(_result_host) or _result_host not in _allowed_redis_hosts:
    raise ImproperlyConfigured(
        f"INTEGRATION_CI_REDIS_RESULT_URL host {_result_host!r} is not allowlisted."
    )

CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_BROKER_URL = _broker_url
CELERY_RESULT_BACKEND = _result_url
# Keep ignore-result behavior from qa/base; integration asserts via email sidecars.
CELERY_TASK_IGNORE_RESULT = True

# Do not inherit a production Redis cache. qa.py already forced LocMem; restate.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "nityadharma-integration-ci-cache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ---------------------------------------------------------------------------
# Email — CI-only recording file backend (no SMTP / Resend / ZeptoMail)
# ---------------------------------------------------------------------------

INTEGRATION_CI_EMAIL_ALLOWED_ROOT = "/tmp/nitya-dharma-integration-mail"
_email_dir = _resolve_email_file_path(_env_required("INTEGRATION_CI_EMAIL_FILE_PATH"))
EMAIL_FILE_PATH = _email_dir
EMAIL_BACKEND = "accounts.tests.ci_email_backend.RecordingFileEmailBackend"
EMAIL_HOST = ""
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
RESEND_API_KEY = ""

ZEPTOMAIL_EMAIL_HOST = ""
ZEPTOMAIL_EMAIL_PORT = 587
ZEPTOMAIL_EMAIL_USE_TLS = True
ZEPTOMAIL_EMAIL_USE_SSL = False
ZEPTOMAIL_EMAIL_HOST_USER = ""
ZEPTOMAIL_EMAIL_HOST_PASSWORD = ""
ZEPTOMAIL_DEFAULT_FROM_EMAIL = ""
ZEPTOMAIL_EMAIL_TIMEOUT = 10
ZEPTOMAIL_ENABLED_FLOWS = frozenset()

DEFAULT_FROM_EMAIL = _require_ci_test_recipient(
    _env_optional(
        "INTEGRATION_CI_DEFAULT_FROM_EMAIL", "integration-ci@example.invalid"
    ),
    label="INTEGRATION_CI_DEFAULT_FROM_EMAIL",
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ADMIN_NOTIFICATION_EMAIL = _require_ci_test_recipient(
    _env_optional(
        "INTEGRATION_CI_ADMIN_NOTIFICATION_EMAIL",
        "integration-ci-admin@example.invalid",
    ),
    label="INTEGRATION_CI_ADMIN_NOTIFICATION_EMAIL",
)

# Test-only ADMINS; recipient must be .invalid / .test.
ADMINS = (
    (
        "Integration CI Ops",
        _require_ci_test_recipient(
            _env_optional(
                "INTEGRATION_CI_ADMIN_EMAIL", "integration-ci-ops@example.invalid"
            ),
            label="INTEGRATION_CI_ADMIN_EMAIL",
        ),
    ),
)

# Clear SMS provider credentials if inherited.
MSG91_AUTH_KEY = ""
SMS_API_KEY = ""
OTP_MODE = _env_optional("OTP_MODE", "mock")
OTP_PROVIDER = _env_optional("OTP_PROVIDER", "mock_sms")

# Role gate consumed by RecordingFileEmailBackend (worker vs test process).
INTEGRATION_CI_EMAIL_ROLE = _env_optional("INTEGRATION_CI_EMAIL_ROLE", "test")
# Optional path to the Celery worker PID file for cross-checks in tests.
INTEGRATION_CI_WORKER_PID_FILE = _env_optional(
    "INTEGRATION_CI_WORKER_PID_FILE", "/tmp/celery-integration-worker.pid"
)
