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

# Database Configuration
# Phase 2 Module 0 Task 0.1: Environment-based database config with SQLite fallback
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': config('DB_NAME', default=str(BASE_DIR / 'db.sqlite3')),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
    }
}

# Email Configuration
# For development: Use SMTP if credentials provided, otherwise console backend
# For production: Configure SMTP settings via environment variables
# Uses config() from python-decouple to read from .env file (automatically loads .env)

# Read email settings using config() (python-decouple automatically loads .env)
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# CRITICAL FIX: Gmail SMTP silently drops emails when DEFAULT_FROM_EMAIL != EMAIL_HOST_USER
# For Gmail SMTP, FROM address MUST match the authenticated account
# If DEFAULT_FROM_EMAIL is set in .env, use it; otherwise default to EMAIL_HOST_USER
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER or 'noreply@nityadharma.com')
SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# Set EMAIL_BACKEND based on whether credentials are provided
# This ensures SMTP is used when credentials exist, console backend otherwise
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
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

