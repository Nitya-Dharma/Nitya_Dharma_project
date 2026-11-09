"""
Minimal Django settings for additive ZeptoMail unit tests.

No MySQL. No production secrets. LocMem email. Empty ZeptoMail allowlist by default.
Used only by accounts.tests.test_additive_zeptomail_providers.
"""

SECRET_KEY = "additive-zeptomail-unit-tests-not-for-production"
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]

MIDDLEWARE = []
ROOT_URLCONF = []
TEMPLATES = []
USE_TZ = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = "gmail-user@example.test"
EMAIL_HOST_PASSWORD = "gmail-app-password-not-real"
DEFAULT_FROM_EMAIL = "gmail-user@example.test"
SERVER_EMAIL = "gmail-user@example.test"
RESEND_API_KEY = ""

ZEPTOMAIL_EMAIL_HOST = ""
ZEPTOMAIL_EMAIL_PORT = 587
ZEPTOMAIL_EMAIL_USE_TLS = True
ZEPTOMAIL_EMAIL_USE_SSL = False
ZEPTOMAIL_EMAIL_HOST_USER = ""
ZEPTOMAIL_EMAIL_HOST_PASSWORD = ""
ZEPTOMAIL_DEFAULT_FROM_EMAIL = ""
ZEPTOMAIL_EMAIL_TIMEOUT = 10
ZEPTOMAIL_ENABLED_FLOWS = frozenset()

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
