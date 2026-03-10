"""
Verify production configuration: email, media, DB, CSV upload.
No secrets are printed. Use on Railway, GoDaddy, VPS, or locally with prod settings.

Usage:
    python manage.py check_production_config
    DJANGO_SETTINGS_MODULE=nityadharma.settings.prod python manage.py check_production_config
    railway ssh -- python manage.py check_production_config
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = "Verify production config: email (SMTP), media, DB, CSV upload. No secrets printed."

    def handle(self, *args, **options):
        errors = []
        self.stdout.write("=== Production configuration check ===\n")

        # --- Email ---
        backend = getattr(settings, "EMAIL_BACKEND", "")
        self.stdout.write(f"EMAIL_BACKEND: {backend}")
        host_set = bool(getattr(settings, "EMAIL_HOST", ""))
        user_set = bool(getattr(settings, "EMAIL_HOST_USER", ""))
        pass_set = bool(getattr(settings, "EMAIL_HOST_PASSWORD", ""))
        resend_key = bool(getattr(settings, "RESEND_API_KEY", ""))
        self.stdout.write(f"  EMAIL_HOST set: {host_set}")
        self.stdout.write(f"  EMAIL_HOST_USER set: {user_set}")
        self.stdout.write(f"  EMAIL_HOST_PASSWORD set: {pass_set}")
        self.stdout.write(f"  RESEND_API_KEY set: {resend_key}")
        from_ok = bool(getattr(settings, "DEFAULT_FROM_EMAIL", ""))
        self.stdout.write(f"  DEFAULT_FROM_EMAIL set: {from_ok}")
        if "resend" in backend.lower():
            self.stdout.write(self.style.SUCCESS("  => Resend is configured (emails will be sent via Resend API)."))
        elif "smtp" in backend.lower():
            self.stdout.write(self.style.SUCCESS("  => SMTP email is configured (emails will be sent)."))
        else:
            self.stdout.write(self.style.WARNING("  => Console backend (emails not sent). For Railway: set RESEND_API_KEY. For GoDaddy/VPS: set EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD."))

        # --- Media (uploads) ---
        self.stdout.write("")
        media_root = getattr(settings, "MEDIA_ROOT", None)
        media_url = getattr(settings, "MEDIA_URL", "")
        self.stdout.write(f"MEDIA_URL: {media_url}")
        if media_root:
            path = str(media_root)
            self.stdout.write(f"MEDIA_ROOT: {path}")
            if os.path.isdir(media_root):
                writable = os.access(media_root, os.W_OK)
                if writable:
                    self.stdout.write(self.style.SUCCESS("  => MEDIA_ROOT exists and is writable."))
                else:
                    self.stdout.write(self.style.WARNING("  => MEDIA_ROOT exists but is not writable."))
            else:
                try:
                    os.makedirs(media_root, exist_ok=True)
                    self.stdout.write(self.style.SUCCESS("  => MEDIA_ROOT created and writable."))
                except OSError as e:
                    errors.append(f"MEDIA_ROOT: {e}")
                    self.stdout.write(self.style.ERROR(f"  => MEDIA_ROOT missing and could not be created: {e}"))
        else:
            self.stdout.write(self.style.WARNING("MEDIA_ROOT not set."))

        # --- Database ---
        self.stdout.write("")
        c = connection.settings_dict
        host = c.get("HOST") or "(none)"
        name = c.get("NAME") or "(none)"
        self.stdout.write(f"DB host: {host}")
        self.stdout.write(f"DB name: {name}")
        try:
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS("  => Database connection OK."))
        except Exception as e:
            errors.append(f"DB: {e}")
            self.stdout.write(self.style.ERROR(f"  => Database connection failed: {e}"))

        # --- CSV upload ---
        self.stdout.write("")
        max_csv = getattr(settings, "FILE_UPLOAD_MAX_CSV_BYTES", None)
        if max_csv is not None:
            self.stdout.write(f"FILE_UPLOAD_MAX_CSV_BYTES: {max_csv} ({max_csv // (1024*1024)} MB)")
        self.stdout.write("  CSV upload: core.file_upload_security.validate_csv_upload (type, size, encoding).")

        self.stdout.write("")
        if errors:
            self.stdout.write(self.style.ERROR("Configuration issues (fix before production):"))
            for e in errors:
                self.stdout.write(self.style.ERROR(f"  - {e}"))
        else:
            self.stdout.write(self.style.SUCCESS("Configuration check complete. No critical issues found."))
