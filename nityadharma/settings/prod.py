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
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())  # Will raise error if not set

# Database Configuration
# Phase 2 Module 0 Task 0.1: Environment-based database config - REQUIRED in production
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE'),  # Required
        'NAME': config('DB_NAME'),  # Required
        'USER': config('DB_USER'),  # Required
        'PASSWORD': config('DB_PASSWORD'),  # Required
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

