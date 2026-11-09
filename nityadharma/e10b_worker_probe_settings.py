"""
E10B Celery worker-probe settings (isolated leaf module).

Selection (explicit only — never the default):
  DJANGO_SETTINGS_MODULE=nityadharma.e10b_worker_probe_settings

Safety:
- Lives OUTSIDE nityadharma.settings so importing this module does not
  execute nityadharma.settings.__init__ (dev/base side-load).
- Does NOT import nityadharma.settings or any of its submodules.
- Refusing DB engine: nityadharma.e10b_refusing_db
- Filebased email only; OTP mock/disabled.
- CELERY_BROKER_URL and CELERY_RESULT_BACKEND independently allowlisted.
- Rejects REDIS_URL / DATABASE_URL / MYSQL_URL / RESEND_API_KEY.
- Registers probe task via CELERY_IMPORTS only.

NOT for production. Do not use as default application settings.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from kombu import Exchange, Queue

# ---------------------------------------------------------------------------
# Env helpers (never log secret values or credential-bearing URLs)
# ---------------------------------------------------------------------------

_FORBIDDEN_ENV = (
    "DATABASE_URL",
    "MYSQL_URL",
    "REDIS_URL",
    "RESEND_API_KEY",
)

_EXPECTED_SETTINGS_MODULE = "nityadharma.e10b_worker_probe_settings"
_DEFAULT_ALLOWED_HOSTS = ("127.0.0.1", "localhost")
_DEFAULT_ALLOWED_PORTS = (6379,)


def _env_required(name: str) -> str:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: missing required environment variable {name}."
        )
    return str(raw).strip()


def _env_optional(name: str, default: str = "") -> str:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip()


def _reject_forbidden_env() -> None:
    for name in _FORBIDDEN_ENV:
        if os.environ.get(name, "").strip():
            raise ImproperlyConfigured(
                f"e10b_worker_probe_settings: {name} must not be set "
                "(disposable CELERY_BROKER_URL / CELERY_RESULT_BACKEND only)."
            )


def _parse_csv_hosts(raw: str) -> frozenset[str]:
    parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    return frozenset(parts)


def _parse_csv_ports(raw: str) -> frozenset[int]:
    ports: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ports.add(int(part))
        except ValueError as exc:
            raise ImproperlyConfigured(
                "e10b_worker_probe_settings: "
                "ZEPTOMAIL_WORKER_PROBE_ALLOWED_BROKER_PORTS must be integers."
            ) from exc
    return frozenset(ports)


def _redact_url_for_error(url: str) -> str:
    """Return a non-secret description of a URL (scheme/host/port/db only)."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "<no-host>"
        port = parsed.port if parsed.port is not None else "<default-port>"
        path = parsed.path or "/"
        return f"{parsed.scheme}://{host}:{port}{path}"
    except Exception:
        return "<unparseable-url>"


def _validate_disposable_broker_url(
    url: str,
    *,
    label: str,
    allowed_hosts: frozenset[str],
    allowed_ports: frozenset[int],
) -> None:
    lowered = url.lower()
    if "memory://" in lowered:
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} must not use memory://."
        )
    if not lowered.startswith("redis://"):
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} must use redis:// "
            "(rediss/amqp not permitted for E10B CI)."
        )

    parsed = urlparse(url)
    if parsed.scheme.lower() != "redis":
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} scheme must be redis."
        )

    # Reject any userinfo (username and/or password), including redis://:pass@host/...
    if parsed.username is not None or parsed.password is not None:
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} must not include username "
            f"or password ({_redact_url_for_error(url)})."
        )
    # Defense in depth: netloc with '@' always means userinfo was present.
    if "@" in (parsed.netloc or ""):
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} must not include userinfo "
            f"({_redact_url_for_error(url)})."
        )

    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} hostname is required."
        )
    if host not in allowed_hosts:
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} hostname {host!r} is not "
            "in the positive disposable allowlist."
        )

    port = parsed.port if parsed.port is not None else 6379
    if port not in allowed_ports:
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} port {port} is not "
            "in the positive disposable allowlist."
        )

    # path like /0 or /1 — database index
    path = (parsed.path or "").strip() or "/"
    db_part = path.lstrip("/")
    if "/" in db_part or not db_part:
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} must include a single "
            "Redis DB index path (e.g. /0)."
        )
    try:
        db_index = int(db_part)
    except ValueError as exc:
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} Redis DB index must be an integer."
        ) from exc
    if db_index < 0 or db_index > 15:
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} Redis DB index must be 0..15."
        )

    # Fail closed on unexpected components that often mark remote/prod URLs.
    if parsed.query or parsed.fragment:
        raise ImproperlyConfigured(
            f"e10b_worker_probe_settings: {label} must not include query/fragment "
            f"({_redact_url_for_error(url)})."
        )


def _validate_email_dir(path_str: str) -> str:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        raise ImproperlyConfigured(
            "e10b_worker_probe_settings: ZEPTOMAIL_WORKER_PROBE_EMAIL_DIR "
            "must be an absolute path."
        )
    forbidden_prefixes = (
        Path("/var/www"),
        Path("/srv"),
        Path("C:/inetpub"),
    )
    for prefix in forbidden_prefixes:
        try:
            if path == prefix or prefix in path.parents:
                raise ImproperlyConfigured(
                    "e10b_worker_probe_settings: email dir must not be under "
                    f"{prefix}."
                )
        except OSError:
            continue
    return str(path)


def _reject_smtp_env() -> None:
    # Hard-fail if classic SMTP credential env is present for this probe.
    for name in ("EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"):
        if os.environ.get(name, "").strip():
            raise ImproperlyConfigured(
                f"e10b_worker_probe_settings: {name} must not be set "
                "(filebased email only)."
            )


# ---------------------------------------------------------------------------
# Fail closed before accepting this settings module
# ---------------------------------------------------------------------------

_configured = os.environ.get("DJANGO_SETTINGS_MODULE", "").strip()
if _configured != _EXPECTED_SETTINGS_MODULE:
    raise ImproperlyConfigured(
        "e10b_worker_probe_settings: DJANGO_SETTINGS_MODULE must be set to "
        f"{_EXPECTED_SETTINGS_MODULE!r} when this module is loaded "
        f"(got {_configured!r} or unset). No silent default."
    )

_reject_forbidden_env()
_reject_smtp_env()

_allowed_hosts = _parse_csv_hosts(
    _env_optional(
        "ZEPTOMAIL_WORKER_PROBE_ALLOWED_BROKER_HOSTS",
        ",".join(_DEFAULT_ALLOWED_HOSTS),
    )
)
if not _allowed_hosts:
    raise ImproperlyConfigured(
        "e10b_worker_probe_settings: broker host allowlist must not be empty."
    )

_allowed_ports = _parse_csv_ports(
    _env_optional(
        "ZEPTOMAIL_WORKER_PROBE_ALLOWED_BROKER_PORTS",
        ",".join(str(p) for p in _DEFAULT_ALLOWED_PORTS),
    )
)
if not _allowed_ports:
    raise ImproperlyConfigured(
        "e10b_worker_probe_settings: broker port allowlist must not be empty."
    )

_broker_url = _env_required("CELERY_BROKER_URL")
_result_backend = _env_required("CELERY_RESULT_BACKEND")
_validate_disposable_broker_url(
    _broker_url,
    label="CELERY_BROKER_URL",
    allowed_hosts=_allowed_hosts,
    allowed_ports=_allowed_ports,
)
_validate_disposable_broker_url(
    _result_backend,
    label="CELERY_RESULT_BACKEND",
    allowed_hosts=_allowed_hosts,
    allowed_ports=_allowed_ports,
)

_email_dir = _validate_email_dir(_env_required("ZEPTOMAIL_WORKER_PROBE_EMAIL_DIR"))

_auth = _env_optional("ZEPTOMAIL_WORKER_PROBE_AUTHORIZED", "")
if _auth and _auth != "YES":
    raise ImproperlyConfigured(
        "e10b_worker_probe_settings: ZEPTOMAIL_WORKER_PROBE_AUTHORIZED "
        "must be unset or YES."
    )

# ---------------------------------------------------------------------------
# Minimal Django configuration
# ---------------------------------------------------------------------------

SECRET_KEY = _env_optional(
    "ZEPTOMAIL_WORKER_PROBE_SECRET_KEY",
    "e10b-celery-worker-probe-not-for-production",
)
DEBUG = False
ALLOWED_HOSTS: list[str] = ["testserver", "localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "accounts",
    "core",
]
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE: list[str] = []
# Empty URLconf embedded here to avoid importing nityadharma.settings.* modules.
ROOT_URLCONF = "nityadharma.e10b_worker_probe_settings"
urlpatterns: list = []
TEMPLATES: list[dict] = []
USE_I18N = False
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Refusing engine — not SQLite/MySQL usable backends.
DATABASES = {
    "default": {
        "ENGINE": "nityadharma.e10b_refusing_db",
        "NAME": "e10b_celery_worker_probe_db_disabled",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "e10b-celery-worker-probe",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = _email_dir
DEFAULT_FROM_EMAIL = _env_optional(
    "DEFAULT_FROM_EMAIL",
    "worker-probe@nityadharma.invalid",
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ---------------------------------------------------------------------------
# Celery — real worker mode (disposable allowlisted broker only)
# ---------------------------------------------------------------------------

CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_BROKER_URL = _broker_url
CELERY_RESULT_BACKEND = _result_backend
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_IGNORE_RESULT = True
CELERY_RESULT_EXPIRES = 300
CELERY_TASK_ACKS_LATE = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_CONCURRENCY = 1
CELERY_TASK_DEFAULT_QUEUE = "emails"
CELERY_TASK_QUEUES = (
    Queue("emails", Exchange("emails", type="direct"), routing_key="emails"),
)
CELERY_TASK_ROUTES = {
    "core.send_email_task_e10b_probe": {"queue": "emails"},
    # If production task is registered via autodiscover, keep it off accidental
    # default queue; E10B producer must never enqueue it.
    "core.send_email_task": {"queue": "emails"},
    "core.tasks_email.send_email_task": {"queue": "emails"},
}
CELERY_IMPORTS = ("core.tasks_email_e10b_probe",)

OTP_MODE = "mock"
OTP_PROVIDER = "mock_sms"
OTP_ENABLED = False
RESEND_API_KEY = ""
MSG91_AUTH_KEY = ""
SMS_API_KEY = ""
