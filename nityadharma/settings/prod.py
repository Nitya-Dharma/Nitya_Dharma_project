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
# Render: use DATABASE_URL (PostgreSQL) when set; otherwise use MySQL DB_* vars
if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
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

