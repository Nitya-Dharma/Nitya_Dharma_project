"""
Django base settings for nityadharma project.

This file contains all common settings shared across all environments.
Environment-specific settings are in dev.py and prod.py
"""

import os
from pathlib import Path

from kombu import Exchange, Queue

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Project apps
    'core',
    'accounts',
    'referrals',
    'masterdata',
    'profiles',
    'dashboards',
    'availability',
    'search',
    'booking_intent',
    'reviews',
    'trust_display',
    'governance',
    'security',
    'maintenance',
    'analytics',
    'behavior_engine',  # Isolated behavior tracking for Newsfeed Intelligence
    'recommendations',
    'pages',
    'notifications',
    'engagement',  # User behavior capture for future news feed
    'tracking_config',  # Super-Admin-only GTM / Analytics configuration
    'support',  # Contact Us system
    'branding',  # Branding Logo Management System
    'ads',  # Super Admin–controlled advertisement banners
    'ads_analytics',  # Ad event tracking, aggregation, and KPI (no change to ad serving)
    'monitoring',  # Phase 12: Observability (no models, no migrations)
    'analytics_dashboard',  # Phase 13: Admin analytics (read-only, no models)
    'recommendation_engine',  # Phase 15: Behavior-driven suggestions (read-only, no models)
    'admin_intelligence',  # Phase 16: Admin intelligence dashboard (read-only, no models)
    'feed_engine',  # Phase 17A: Personalized feed ranking engine
    'services',
    'otp_verification',  # Phase 2 Task 1: isolated pre-registration OTP foundation
]

# Custom User Model
# Must be set before first migration
AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware_session_validation.SessionValidationMiddleware',  # TASK 18: Force logout for deactivated users
    'django.contrib.messages.middleware.MessageMiddleware',
    'behavior_engine.middleware.PageViewTrackingMiddleware',  # Phase 14: page view tracking (GET only)
    'monitoring.middleware.RequestTimingMiddleware',  # Phase 12: request timing (observational only)
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nityadharma.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.navbar_context',  # Global navbar context
                'nityadharma.context_processors.pooja_data',  # Global navbar pooja aliases
                'tracking_config.context_processors.tracking_context',  # Super-Admin-only tracking injection
                'pages.context_processors.social_links',  # Global social media links
                'ads.context_processors.active_ads',  # Super Admin–controlled ad placements
            ],
        },
    },
]

WSGI_APPLICATION = 'nityadharma.wsgi.app'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
# Database configuration is environment-specific and defined in dev.py and prod.py
# SQLite fallback (commented - use MySQL in dev/prod):
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password reset timeout (in seconds)
# Default: 3 days (259200), Set to 24 hours (86400) for better security
PASSWORD_RESET_TIMEOUT = 86400  # 24 hours

# Cache configuration (django-redis when REDIS_URL is set; safe fallback otherwise).
# Docker Compose sets REDIS_URL=redis://redis:6379/1 on the web service.
# IGNORE_EXCEPTIONS: django-redis swallows connection errors so views keep working if Redis stops.
_LOC_MEM_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'nityadharma-cache',
    }
}

try:
    import django_redis  # noqa: F401

    _redis_url = os.environ.get('REDIS_URL', '').strip()
    if _redis_url:
        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': _redis_url,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'IGNORE_EXCEPTIONS': True,
                },
            }
        }
        # Shared session store across Gunicorn workers (use DB sessions when Redis is off).
        SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
        SESSION_CACHE_ALIAS = 'default'
    else:
        CACHES = _LOC_MEM_CACHES
except Exception:
    CACHES = _LOC_MEM_CACHES

# Celery (optional background worker). REDIS_URL unchanged for cache/sessions.
# Prefer CELERY_BROKER_URL / CELERY_RESULT_BACKEND (e.g. Redis DB 2) to separate from Django cache (often DB 1).
CELERY_BROKER_URL = os.getenv(
    'CELERY_BROKER_URL',
    os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = os.getenv(
    'CELERY_RESULT_BACKEND',
    os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
)
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
# Result backend TTL (seconds) — limits growth of Celery result keys in Redis.
CELERY_RESULT_EXPIRES = 3600  # 1 hour
# Safe default: do not store task results unless a task explicitly opts in.
CELERY_TASK_IGNORE_RESULT = True

# Queue layout (preparation only; tasks keep default routing until CELERY_TASK_ROUTES assigns them).
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = (
    Queue('default', Exchange('default', type='direct'), routing_key='default'),
    Queue('emails', Exchange('emails', type='direct'), routing_key='emails'),
    Queue('analytics', Exchange('analytics', type='direct'), routing_key='analytics'),
)
CELERY_TASK_ROUTES = {
    'core.tasks_email.send_email_task': {'queue': 'emails'},
    'notifications.tasks.send_notification_task': {'queue': 'default'},
    'analytics.tasks.log_analytics_task': {'queue': 'analytics'},
}

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Media files (User-uploaded content)
# https://docs.djangoproject.com/en/6.0/topics/files/
# Use leading slash for production compatibility (Railway, GoDaddy, VPS, Docker).
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
# https://docs.djangoproject.com/en/6.0/ref/settings/#login-url
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Phase 9: Security hardening (safe defaults; Secure cookie flags are env-driven in dev/prod)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'
# Explicit session lifetime and sliding refresh (same for DB or Redis cache backend)
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Logging Configuration
# Phase 2 Module 0 Task 0.1: Centralized logging foundation
# Phase 2 Module 0 Task 0.5: Logging strategy - observational only, no PII, no payloads
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'suppress_chrome_devtools_404': {
            '()': 'core.log_filters.SuppressChromeDevTools404',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['suppress_chrome_devtools_404'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
# Logging Rules (Phase 2 Module 0 Task 0.5):
# ✅ Allowed: System startup errors, Configuration failures, Unexpected exceptions, Infrastructure warnings
# ❌ Forbidden: PII, Credentials, Tokens, Request payloads, Business decision traces
# 📌 Errors are admin-visible only

# File upload max sizes (used by core.file_upload_security and gallery uploads)
# Image limit: 20 MB project-wide for profile, cover, gallery, logos, ads (consistent across all roles)
FILE_UPLOAD_MAX_IMAGE_BYTES = 20 * 1024 * 1024   # 20 MB per image
FILE_UPLOAD_MAX_CSV_BYTES = 5 * 1024 * 1024     # 5 MB per CSV (master data uploads)

def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default

# Pre-registration SMS OTP (Phase 2 — delivery providers; defaults keep mock offline)
OTP_ENABLED = _env_bool("OTP_ENABLED", False)
# Durable challenge store for multi-worker (Task 8). Use "memory" only for
# single-worker rollback / isolated tests that do not inject a repository.
OTP_CHALLENGE_STORAGE = (
    os.environ.get("OTP_CHALLENGE_STORAGE", "database").strip().lower() or "database"
)
OTP_MODE = os.environ.get("OTP_MODE", "mock").strip() or "mock"
OTP_PROVIDER = os.environ.get("OTP_PROVIDER", "mock_sms").strip() or "mock_sms"
OTP_PROVIDER_ENABLED = _env_bool("OTP_PROVIDER_ENABLED", True)
OTP_PROVIDER_AUDIT_ENABLED = _env_bool("OTP_PROVIDER_AUDIT_ENABLED", True)
OTP_PROVIDER_METRICS_ENABLED = _env_bool("OTP_PROVIDER_METRICS_ENABLED", True)
OTP_EXPIRY_SECONDS = max(1, _env_int("OTP_EXPIRY_SECONDS", 600))
OTP_LENGTH = max(4, _env_int("OTP_LENGTH", 6))
OTP_MAX_ATTEMPTS = max(1, _env_int("OTP_MAX_ATTEMPTS", 5))
OTP_MAX_RESENDS = max(0, _env_int("OTP_MAX_RESENDS", 3))
OTP_RESEND_COOLDOWN_SECONDS = max(0, _env_int("OTP_RESEND_COOLDOWN_SECONDS", 60))
# Pending registration session TTL (default 15 minutes). Expired sessions cannot resume.
OTP_REGISTRATION_PENDING_TTL_SECONDS = max(
    60, _env_int("OTP_REGISTRATION_PENDING_TTL_SECONDS", 900)
)
# Idempotent completed-marker TTL (default 30 minutes).
OTP_REGISTRATION_COMPLETED_TTL_SECONDS = max(
    60, _env_int("OTP_REGISTRATION_COMPLETED_TTL_SECONDS", 1800)
)
OTP_MOCK_SIMULATION_MODE = os.environ.get("OTP_MOCK_SIMULATION_MODE", "success").strip() or "success"
OTP_MOCK_EXECUTION_DELAY_MS = max(0, _env_int("OTP_MOCK_EXECUTION_DELAY_MS", 0))
OTP_MOCK_ALLOW_RANDOM = _env_bool("OTP_MOCK_ALLOW_RANDOM", False)
MSG91_AUTH_KEY = os.environ.get("MSG91_AUTH_KEY", "").strip()
MSG91_BASE_URL = (
    os.environ.get("MSG91_BASE_URL", "https://control.msg91.com/api/v5/flow/").strip()
    or "https://control.msg91.com/api/v5/flow/"
)
MSG91_FLOW_ID = os.environ.get("MSG91_FLOW_ID", "").strip()
MSG91_SENDER_ID = os.environ.get("MSG91_SENDER_ID", "").strip()
MSG91_TEMPLATE_VARIABLE = os.environ.get("MSG91_TEMPLATE_VARIABLE", "OTP").strip() or "OTP"
MSG91_COUNTRY_CODE = os.environ.get("MSG91_COUNTRY_CODE", "91").strip() or "91"
MSG91_TIMEOUT_SECONDS = max(1, _env_int("MSG91_TIMEOUT_SECONDS", 10))
# broadcast.run / Omni SMS (OTP_PROVIDER=broadcast_sms)
SMS_API_KEY = os.environ.get("SMS_API_KEY", "").strip()
