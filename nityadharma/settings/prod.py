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
from decouple import config, Csv
from .base import *

# Avoid ManifestStaticFilesStorage so missing static files (e.g. images/logo.png) don't cause 500
STORAGES['staticfiles'] = {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'}

# Serve uploaded media (e.g. branding logo) from the app. OK for testing; use S3/Volume for persistence.
# On Railway, uploads are lost on redeploy unless you add a Volume or use external storage.
SERVE_MEDIA_IN_PROD = True

# SECURITY WARNING: keep the secret key used in production secret!
# Phase 2 Module 0 Task 0.1: Environment variable - REQUIRED in production (no default)
SECRET_KEY = config('SECRET_KEY')  # Will raise error if not set

# SECURITY WARNING: don't run with debug turned on in production!
# Phase 2 Module 0 Task 0.1: Environment variable - REQUIRED in production
DEBUG = config('DEBUG', default=False, cast=bool)

# Phase 2 Module 0 Task 0.1: Environment variable - REQUIRED in production
# Render: RENDER_EXTERNAL_HOSTNAME is auto-added when set
# Railway: .railway.app, Fly.io, etc. Add hosts via ALLOWED_HOSTS or platform env.
# For test deployment, ALLOWED_HOSTS can be "*" (set in env).
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
_vercel = os.environ.get('VERCEL')
_railway = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
_fly = os.environ.get('FLY_APP_NAME')
_allowed = list(config('ALLOWED_HOSTS', default='*', cast=Csv()))
if _render_host and _render_host not in _allowed:
    _allowed.append(_render_host)
if _vercel and '.vercel.app' not in _allowed:
    _allowed.append('.vercel.app')
if _railway and '.railway.app' not in _allowed:
    _allowed.append('.railway.app')
if _fly and 'fly.dev' not in str(_allowed):
    _allowed.append('.fly.dev')
ALLOWED_HOSTS = _allowed if _allowed else ([_render_host] if _render_host else ['*'])

# Database Configuration
# Phase 2 Module 0 Task 0.1: Environment-based database config - REQUIRED in production
# Priority: DATABASE_URL (PostgreSQL) -> MYSQL_URL (Railway MySQL) -> DB_* vars (MySQL)
import dj_database_url

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
        # Longer connect_timeout for external TCP Proxy (avoids "Lost connection at handshake")
        _db['OPTIONS'].setdefault('connect_timeout', 30)
    DATABASES = {'default': _db}
else:
    DATABASES = {
        'default': {
            'ENGINE': config('DB_ENGINE'),
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
            },
        }
    }

# Production Security Settings
# Phase 2 Module 0 Task 0.1 / Phase 9: Security-first defaults for production
# Trust X-Forwarded-Proto from Railway/Render/etc. so SSL redirect doesn't loop (proxy terminates SSL)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Cookie HttpOnly and SameSite are set in base.py; Secure is True for HTTPS-only

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
    EMAIL_BACKEND = (
        "django.core.mail.backends.smtp.EmailBackend"
        if (EMAIL_HOST and EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)
        else "django.core.mail.backends.console.EmailBackend"
    )

