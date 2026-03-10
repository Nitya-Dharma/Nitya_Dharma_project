"""
Django development settings for nityadharma project.

This file imports all common settings from base.py and adds
development-specific configurations.

Phase 2 Module 0 Task 0.1: Environment Configuration
- Uses environment variables with safe defaults for development
- Forgiving defaults allow development without .env file
"""

import os
from decouple import config, Csv
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
# Phase 2 Module 0 Task 0.1: Environment variable with safe default for dev
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# Phase 2 Module 0 Task 0.1: Environment variable with safe default for dev
DEBUG = config('DEBUG', default=True, cast=bool)

# Phase 2 Module 0 Task 0.1: Environment variable with safe default for dev
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

# Site URL for building absolute URLs (email verification links, etc.)
# Use 127.0.0.1:8000 for local development (not localhost to avoid DNS issues)
SITE_URL = config('SITE_URL', default='http://127.0.0.1:8000')

# Phase 9: Keep SSL redirect off locally; production uses SECURE_SSL_REDIRECT=True
SECURE_SSL_REDIRECT = False
# Secure cookies off for local HTTP; production sets SESSION_COOKIE_SECURE/CSRF_COOKIE_SECURE via prod.py
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Database Configuration
# Phase 2 Module 0 Task 0.1: Environment-based database config with SQLite fallback
# Phase 4: MySQL for local development (Schema Clone). Set DB_* in .env to override.
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.mysql'),
        'NAME': config('DB_NAME', default='nityadharma_db'),
        'USER': config('DB_USER', default='nitya_user'),
        'PASSWORD': config('DB_PASSWORD', default='StrongPassword123!'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
        # Phase 11F.1: Stable test database name so Django creates/destroys it consistently
        'TEST': {
            'NAME': 'test_nityadharma_db',
        },
    }
}

# Email Configuration
# For development: Use SMTP if credentials provided, otherwise console backend
# For production: Configure SMTP settings via environment variables
# Uses config() from python-decouple to read from .env file (automatically loads .env)

# Read email settings (same env vars as prod: GoDaddy, VPS, Railway use these)
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Gmail/GoDaddy: DEFAULT_FROM_EMAIL should match authenticated account for delivery
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER or 'noreply@nityadharma.com')
SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# Use SMTP only when all three are set (same as prod)
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if (EMAIL_HOST and EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)
    else "django.core.mail.backends.console.EmailBackend"
)

# TASK 4: Hard fail on misconfiguration (DEV ONLY)
# Gmail SMTP requires FROM address to match authenticated account
# This prevents silent email drops
if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    if EMAIL_HOST_USER and DEFAULT_FROM_EMAIL != EMAIL_HOST_USER:
        import logging
        logger = logging.getLogger(__name__)
        logger.error("=" * 80)
        logger.error("EMAIL CONFIGURATION ERROR - Gmail SMTP will silently drop emails!")
        logger.error("=" * 80)
        logger.error(f"EMAIL_HOST_USER: {EMAIL_HOST_USER}")
        logger.error(f"DEFAULT_FROM_EMAIL: {DEFAULT_FROM_EMAIL}")
        logger.error("=" * 80)
        logger.error("Gmail SMTP requires DEFAULT_FROM_EMAIL == EMAIL_HOST_USER")
        logger.error("Change .env: DEFAULT_FROM_EMAIL={EMAIL_HOST_USER}")
        logger.error("=" * 80)
        
        # In DEBUG mode, raise exception to prevent silent failures
        if DEBUG:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                f"Gmail SMTP misconfiguration detected. "
                f"EMAIL_HOST_USER ({EMAIL_HOST_USER}) != DEFAULT_FROM_EMAIL ({DEFAULT_FROM_EMAIL}). "
                f"Gmail will silently drop emails. "
                f"Fix: Set DEFAULT_FROM_EMAIL={EMAIL_HOST_USER} in .env file."
            )

