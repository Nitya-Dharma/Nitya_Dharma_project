"""
Send one test email to verify SMTP is working (e.g. on Railway).
No secrets are printed. Use after setting EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD.

Usage:
    python manage.py send_test_email your@email.com
    railway ssh -- python manage.py send_test_email your@email.com
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail


class Command(BaseCommand):
    help = "Send a test email to the given address to verify SMTP configuration."

    def add_arguments(self, parser):
        parser.add_argument(
            "email",
            type=str,
            help="Email address to send the test message to (e.g. your@gmail.com)",
        )

    def handle(self, *args, **options):
        to_email = options["email"].strip()
        backend = getattr(settings, "EMAIL_BACKEND", "")
        if "console" in backend.lower():
            self.stdout.write(
                self.style.WARNING(
                    "EMAIL_BACKEND is console. Set EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD in env to send real emails."
                )
            )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")
        try:
            n = send_mail(
                subject="[Nitya Dharma] Test email",
                message="If you receive this, SMTP is configured correctly for Pandit registration emails.",
                from_email=from_email,
                recipient_list=[to_email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Sent test email to {to_email} (result={n}). Check inbox and spam."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send: {e}"))
