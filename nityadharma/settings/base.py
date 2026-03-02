"""
Django base settings for nityadharma project.

This file contains all common settings shared across all environments.
Environment-specific settings are in dev.py and prod.py
"""

from pathlib import Path

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
]

# Custom User Model
# Must be set before first migration
AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware_session_validation.SessionValidationMiddleware',  # TASK 18: Force logout for deactivated users
    'django.contrib.messages.middleware.MessageMiddleware',
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
                'tracking_config.context_processors.tracking_context',  # Super-Admin-only tracking injection
                'pages.context_processors.social_links',  # Global social media links
                'ads.context_processors.active_ads',  # Super Admin–controlled ad placements
            ],
        },
    },
]

WSGI_APPLICATION = 'nityadharma.wsgi.application'


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

# Cache Configuration
# Used for rate limiting and session storage
# Development: Use local memory cache (simple, no setup required)
# Production: Should use Redis or Memcached
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'nityadharma-cache',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/
STATIC_URL = 'static/'
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
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
# https://docs.djangoproject.com/en/6.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication URLs
# https://docs.djangoproject.com/en/6.0/ref/settings/#login-url
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

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
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
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

