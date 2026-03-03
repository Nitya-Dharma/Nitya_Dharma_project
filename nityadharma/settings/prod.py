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
# Vercel: .vercel.app is auto-added when VERCEL=1
# Railway: .railway.app is auto-added when RAILWAY_PUBLIC_DOMAIN is set
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
_vercel = os.environ.get('VERCEL')
_railway = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
_allowed = list(config('ALLOWED_HOSTS', default='', cast=Csv()))
if _render_host and _render_host not in _allowed:
    _allowed.append(_render_host)
if _vercel and '.vercel.app' not in _allowed:
    _allowed.append('.vercel.app')
if _railway and '.railway.app' not in _allowed:
    _allowed.append('.railway.app')
ALLOWED_HOSTS = _allowed if _allowed else ([_render_host] if _render_host else ['localhost'])

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
# Phase 2 Module 0 Task 0.1: Security-first defaults for production
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)

