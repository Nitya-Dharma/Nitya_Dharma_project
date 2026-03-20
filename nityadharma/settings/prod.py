"""
Django production settings for nityadharma project.

This file imports all common settings from base.py and adds
production-specific configurations.

Phase 2 Module 0 Task 0.1: Environment Configuration
- Strict environment variable requirements (no defaults)
- Fail-fast on missing required variables
- Secure defaults enforced
"""

import os
import logging
from decouple import config, Csv
from .base import *

# Ensure logs directory exists for production error logging.
# In Docker we persist logs into /logs via a volume.
_log_dir = os.environ.get("LOG_DIR", "").strip() or "/logs"
os.makedirs(_log_dir, exist_ok=True)

# Avoid ManifestStaticFilesStorage so missing static files (e.g. images/logo.png) don't cause 500
STORAGES['staticfiles'] = {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'}

# Serve uploaded media (e.g. branding logo) from the app. OK for testing; use S3/Volume for persistence.
# On Railway, uploads are lost on redeploy unless you add a Volume or use external storage.
SERVE_MEDIA_IN_PROD = True

# Persistent media on Railway: set MEDIA_ROOT to a path on a Railway Volume (e.g. /data/media).
# In Railway: add a Volume with mount path /data, then set env MEDIA_ROOT=/data/media (or RAILWAY_VOLUME_MOUNT_PATH=/data and we use /data/media).
_volume_path = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', '').strip()
_media_root_env = os.environ.get('MEDIA_ROOT', '').strip()
if _media_root_env:
    MEDIA_ROOT = _media_root_env
elif _volume_path:
    MEDIA_ROOT = os.path.join(_volume_path, 'media')
else:
    # Default from base: BASE_DIR / 'media' (ephemeral on Railway; fine for GoDaddy VPS persistent disk)
    pass

# SECURITY WARNING: keep the secret key used in production secret!
# Phase 2 Module 0 Task 0.1: Environment variable - REQUIRED in production (no default)
SECRET_KEY = config('SECRET_KEY')  # Will raise error if not set

# SECURITY WARNING: don't run with debug turned on in production!
# Always False in prod; ignore env so deploy check and VPS never expose debug.
DEBUG = False

# Phase 2 Module 0 Task 0.1: Environment variable - REQUIRED in production
# Render: RENDER_EXTERNAL_HOSTNAME is auto-added when set
# Railway: .railway.app, Fly.io, etc. Add hosts via ALLOWED_HOSTS or platform env.
# Production: set ALLOWED_HOSTS in env (e.g. yourdomain.com,www.yourdomain.com,server-ip). No default "*".
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
_vercel = os.environ.get('VERCEL')
_railway = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
_fly = os.environ.get('FLY_APP_NAME')
_allowed = [h.strip() for h in config('ALLOWED_HOSTS', default='', cast=Csv()) if h and h.strip()]
if _render_host and _render_host not in _allowed:
    _allowed.append(_render_host)
if _vercel and '.vercel.app' not in _allowed:
    _allowed.append('.vercel.app')
if _railway and '.railway.app' not in _allowed:
    _allowed.append('.railway.app')
if _fly and 'fly.dev' not in str(_allowed):
    _allowed.append('.fly.dev')
ALLOWED_HOSTS = _allowed if _allowed else ([_render_host] if _render_host else [])

# Database Configuration
# Phase 2 Module 0 Task 0.1: Environment-based database config - REQUIRED in production
# Priority: DATABASE_URL (PostgreSQL) -> MYSQL_URL (Railway MySQL) -> DATABASE_* / DB_* (MySQL for VPS)
# Hostinger VPS: use DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD, DATABASE_HOST, DATABASE_PORT
import dj_database_url

def _mysql_db_from_env():
    # Prefer DATABASE_* (Hostinger/VPS convention), fall back to DB_* (existing)
    name = os.getenv('DATABASE_NAME') or config('DB_NAME', default='')
    user = os.getenv('DATABASE_USER') or config('DB_USER', default='')
    pwd = os.getenv('DATABASE_PASSWORD') or config('DB_PASSWORD', default='')
    host = os.getenv('DATABASE_HOST') or config('DB_HOST', default='localhost')
    port = os.getenv('DATABASE_PORT') or config('DB_PORT', default='3306')
    engine = os.getenv('DB_ENGINE') or config('DB_ENGINE', default='django.db.backends.mysql')
    return {
        'ENGINE': engine,
        'NAME': name,
        'USER': user,
        'PASSWORD': pwd,
        'HOST': host,
        'PORT': port,
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }

if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif os.environ.get('MYSQL_URL'):
    # Railway MySQL template exposes MYSQL_URL (mysql://user:pass@host:port/dbname)
    _db = dj_database_url.parse(
        os.environ['MYSQL_URL'],
        conn_max_age=600,
        conn_health_checks=True,
    )
    if _db.get('ENGINE', '').endswith('mysql'):
        _db.setdefault('OPTIONS', {})['charset'] = 'utf8mb4'
        _db['OPTIONS'].setdefault('connect_timeout', 30)
        _db['OPTIONS'].setdefault('init_command', "SET sql_mode='STRICT_TRANS_TABLES'")
    DATABASES = {'default': _db}
else:
    DATABASES = {'default': _mysql_db_from_env()}

# Production Security Settings
# Phase 2 Module 0 Task 0.1 / Phase 9: Security-first defaults for production
# Trust X-Forwarded-Proto from Railway/Render/etc. so SSL redirect doesn't loop (proxy terminates SSL)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Production hardening: always redirect to HTTPS.
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
DEBUG_PROPAGATE_EXCEPTIONS = False
# Mask sensitive POST parameters in error reports and logs (no form/request logic change)
SENSITIVE_POST_PARAMETERS = ["password"]
# HSTS: only enable when the whole site is served over HTTPS (e.g. VPS behind SSL).
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Cookie HttpOnly and SameSite are set in base.py; Secure is True for HTTPS-only

# Production logging: rotating files sized for 8GB RAM (Hostinger KVM2); errors and warnings
# RotatingFileHandler: 10MB per file, 5 backups (~60MB max) — safe for 8GB
_log_file = os.path.join(_log_dir, 'django.log')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': _log_file,
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'file_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(_log_dir, 'django_errors.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'file_errors'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'file_errors'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Upload limits: allow images up to 20 MB; prevents abuse beyond that (no change to application logic)
_DATA_FILE_MAX = 20 * 1024 * 1024   # 20 MB (must be >= FILE_UPLOAD_MAX_IMAGE_BYTES in base)
DATA_UPLOAD_MAX_MEMORY_SIZE = _DATA_FILE_MAX
FILE_UPLOAD_MAX_MEMORY_SIZE = _DATA_FILE_MAX

# Optional Redis caching for production (safe fallback: runs without Redis if REDIS_URL not set)
_redis_url = os.environ.get('REDIS_URL', '').strip()
if _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _redis_url,
        }
    }
# else: keep base.py CACHES (LocMemCache) so system runs normally without Redis

# ---------------------------------------------------------------------------
# Email (production) — env-only, no secrets in code.
# Railway Free/Hobby blocks outbound SMTP (port 587) → use Resend (HTTPS) when on Railway.
# Priority: RESEND_API_KEY → SMTP (EMAIL_HOST + USER + PASSWORD) → console.
# ---------------------------------------------------------------------------
_resend_key = os.environ.get('RESEND_API_KEY', '').strip()
_email_host = os.environ.get('EMAIL_HOST', '').strip()
_email_user = os.environ.get('EMAIL_HOST_USER', '').strip()
_email_pass = os.environ.get('EMAIL_HOST_PASSWORD', '').strip()

if _resend_key:
    # Resend over HTTPS — works when SMTP is blocked (e.g. Railway Free/Hobby).
    EMAIL_BACKEND = "core.email_backends.ResendBackend"
    RESEND_API_KEY = _resend_key
    RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', '').strip() or config('RESEND_FROM_EMAIL', default='Nitya Dharma <onboarding@resend.dev>')
    DEFAULT_FROM_EMAIL = RESEND_FROM_EMAIL or config('DEFAULT_FROM_EMAIL', default='Nitya Dharma <onboarding@resend.dev>')
    SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
    EMAIL_HOST = EMAIL_PORT = EMAIL_USE_TLS = EMAIL_USE_SSL = None
    EMAIL_HOST_USER = EMAIL_HOST_PASSWORD = ''
else:
    # SMTP for GoDaddy, VPS, or any host that allows outbound SMTP
    EMAIL_HOST = _email_host or config('EMAIL_HOST', default='')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
    # GoDaddy port 465: set EMAIL_PORT=465, EMAIL_USE_SSL=True, EMAIL_USE_TLS=False
    EMAIL_HOST_USER = _email_user or config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = _email_pass or config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER or 'noreply@nityadharma.com')
    SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
    # Prevents SMTP hangs if the mail server is slow or unreachable
    EMAIL_TIMEOUT = 10
    EMAIL_BACKEND = (
        "django.core.mail.backends.smtp.EmailBackend"
        if (EMAIL_HOST and EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)
        else "django.core.mail.backends.console.EmailBackend"
    )

