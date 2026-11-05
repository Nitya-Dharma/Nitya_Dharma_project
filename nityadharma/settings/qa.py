"""
Fail-closed QA settings for Nitya Dharma (ZeptoMail / email path isolation).

Selection (explicit only — never the default):
  DJANGO_SETTINGS_MODULE=nityadharma.settings.qa
  or: python manage.py … --settings=nityadharma.settings.qa

Safety properties:
- Does not alter dev.py / prod.py / base.py / __init__.py.
- Does not load .env via python-decouple for DB or email credentials.
- Requires explicit QA_DB_* process environment variables (no silent defaults).
- Rejects DATABASE_URL / MYSQL_URL (ambiguous / prod-prone).
- Rejects known production-like DB names.
- Accepts QA_DB_HOST only when it exactly matches an entry in QA_ALLOWED_DB_HOSTS
  (fail-closed if that allowlist is unset/empty). Localhost / loopback never allowed.
- Forces locmem email (no SMTP / Resend).
- Forces eager Celery and overrides broker/result away from inherited Redis URLs.
- Forces LocMem cache and database sessions (no inherited REDIS_URL cache).

This module only defines configuration. Importing it must not open DB/SMTP/Redis
sockets; connections occur only if a later process uses Django's DB/cache/email APIs.
Do not use this module against development or production databases.
"""

from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

# ---------------------------------------------------------------------------
# Helpers (env-only; never python-decouple / .env for QA isolation)
# ---------------------------------------------------------------------------

def _env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(
            f"QA settings require process env {name}=… "
            f"(no default; .env is not consulted for this key)."
        )
    return value


def _env_optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# ---------------------------------------------------------------------------
# Core identity
# ---------------------------------------------------------------------------

SECRET_KEY = _env_required("QA_SECRET_KEY")
DEBUG = _env_optional("QA_DEBUG", "False").lower() in ("1", "true", "yes", "on")
ALLOWED_HOSTS = [
    h.strip()
    for h in _env_optional("QA_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if h.strip()
]
SITE_URL = _env_optional("QA_SITE_URL", "http://127.0.0.1:8000")

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ---------------------------------------------------------------------------
# Database — fail-closed (configuration only; no connection opened here)
# ---------------------------------------------------------------------------

# Forbid URL-based DB resolution entirely in QA (prod.py uses these).
if os.environ.get("DATABASE_URL", "").strip():
    raise ImproperlyConfigured(
        "QA settings reject DATABASE_URL. Use explicit QA_DB_* variables only."
    )
if os.environ.get("MYSQL_URL", "").strip():
    raise ImproperlyConfigured(
        "QA settings reject MYSQL_URL. Use explicit QA_DB_* variables only."
    )

_QA_FORBIDDEN_DB_NAMES = frozenset(
    {
        "nityadharma_db",  # common project default / compose default
        "mysql",
        "information_schema",
        "performance_schema",
        "sys",
    }
)

# Always-rejected host forms (never allowlisted; no localhost bypass exists).
_QA_FORBIDDEN_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "*",
        "",
    }
)


def _is_forbidden_qa_host(host: str) -> bool:
    """True for loopback, unspecified, wildcard, or empty host forms."""
    h = (host or "").strip()
    if not h:
        return True
    hl = h.lower()
    if hl in _QA_FORBIDDEN_HOSTS:
        return True
    if "*" in h:
        return True
    # IPv4 loopback net and unspecified
    if hl.startswith("127.") or hl == "0.0.0.0":
        return True
    # Bare IPv6 loopback / unspecified variants
    if hl in {"::", "::0", "0:0:0:0:0:0:0:0", "0:0:0:0:0:0:0:1"}:
        return True
    return False


_db_engine = _env_required("QA_DB_ENGINE")
_db_name = _env_required("QA_DB_NAME")
_db_user = _env_required("QA_DB_USER")
_db_password = _env_required("QA_DB_PASSWORD")
_db_host = _env_required("QA_DB_HOST")
_db_port = _env_required("QA_DB_PORT")

if _db_engine != "django.db.backends.mysql":
    raise ImproperlyConfigured(
        "QA settings currently allow only django.db.backends.mysql "
        f"(got {_db_engine!r}). SQLite is not approved for QA app-path isolation."
    )

if _db_name.lower() in _QA_FORBIDDEN_DB_NAMES:
    raise ImproperlyConfigured(
        f"QA_DB_NAME={_db_name!r} is forbidden (production-like or system schema)."
    )

if not _db_password:
    raise ImproperlyConfigured("QA_DB_PASSWORD must be non-empty.")

# Strict host allowlist: must be supplied explicitly in process env.
# No built-in QA hostname is invented here. Until ops sets QA_ALLOWED_DB_HOSTS
# to a separately approved disposable QA endpoint, every host is rejected.
_raw_allowed_hosts = _env_required("QA_ALLOWED_DB_HOSTS")
_allowed_hosts: list[str] = []
for _entry in _raw_allowed_hosts.split(","):
    _candidate = _entry.strip()
    if not _candidate:
        continue
    if _is_forbidden_qa_host(_candidate):
        raise ImproperlyConfigured(
            "QA_ALLOWED_DB_HOSTS contains a forbidden host form "
            f"({_candidate!r}). Localhost, loopback, unspecified and "
            "wildcard entries are never permitted."
        )
    _allowed_hosts.append(_candidate)

if not _allowed_hosts:
    raise ImproperlyConfigured(
        "QA_ALLOWED_DB_HOSTS must list at least one approved disposable QA "
        "database hostname or IP (comma-separated). No host is accepted until "
        "an explicit approved value is configured."
    )

if _is_forbidden_qa_host(_db_host):
    raise ImproperlyConfigured(
        f"QA_DB_HOST={_db_host!r} is a forbidden host form "
        "(localhost / loopback / unspecified / wildcard)."
    )

# Exact match against the approved allowlist (no private-network shortcuts).
if _db_host not in _allowed_hosts:
    raise ImproperlyConfigured(
        f"QA_DB_HOST={_db_host!r} is not in QA_ALLOWED_DB_HOSTS. "
        "Only an exactly matching, separately approved QA endpoint is accepted."
    )

DATABASES = {
    "default": {
        "ENGINE": _db_engine,
        "NAME": _db_name,
        "USER": _db_user,
        "PASSWORD": _db_password,
        "HOST": _db_host,
        "PORT": _db_port,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {
            # Distinct from dev.py's test_nityadharma_db default.
            "NAME": _env_optional("QA_DB_TEST_NAME", f"test_{_db_name}") or f"test_{_db_name}",
        },
    }
}

# ---------------------------------------------------------------------------
# Email — hard isolation (no SMTP / Resend; ignore inherited credentials)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
EMAIL_HOST = ""
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
# Clear any Resend signal that prod.py would honor; QA never selects ResendBackend.
RESEND_API_KEY = ""
DEFAULT_FROM_EMAIL = _env_optional(
    "QA_DEFAULT_FROM_EMAIL", "qa-noreply@example.invalid"
)
SERVER_EMAIL = _env_optional("QA_SERVER_EMAIL", DEFAULT_FROM_EMAIL)
ADMIN_NOTIFICATION_EMAIL = _env_optional(
    "QA_ADMIN_NOTIFICATION_EMAIL", "qa-admin@example.invalid"
)

# ---------------------------------------------------------------------------
# Cache / sessions — no inherited Redis
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "nityadharma-qa-cache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"
# Drop Redis session aliases if base enabled them under REDIS_URL.
if "SESSION_CACHE_ALIAS" in globals():
    del SESSION_CACHE_ALIAS  # noqa: F821

# ---------------------------------------------------------------------------
# Celery — eager in-process; do not inherit production/localhost Redis broker
# ---------------------------------------------------------------------------

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
# memory:// avoids using REDIS_URL / localhost Redis from base.py defaults.
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_TASK_IGNORE_RESULT = True

# ---------------------------------------------------------------------------
# Operator notes (non-secret)
# ---------------------------------------------------------------------------
# Required env (examples — do not commit real values):
#   QA_SECRET_KEY
#   QA_DB_ENGINE=django.db.backends.mysql
#   QA_DB_NAME=<qa-only database name, not nityadharma_db>
#   QA_DB_USER=<qa-only user>
#   QA_DB_PASSWORD=<qa-only password>
#   QA_DB_HOST=<must exactly match one QA_ALLOWED_DB_HOSTS entry>
#   QA_DB_PORT=3306
#   QA_ALLOWED_DB_HOSTS=<approved disposable QA host only; comma-separated>
# Optional:
#   QA_DEFAULT_FROM_EMAIL / QA_SERVER_EMAIL / QA_ADMIN_NOTIFICATION_EMAIL
#
# Never point QA_DB_* at development or production databases.
# Never put localhost / 127.0.0.1 / ::1 / 0.0.0.0 / * in QA_ALLOWED_DB_HOSTS.
# There is no QA_ALLOW_LOCALHOST_DB bypass.
