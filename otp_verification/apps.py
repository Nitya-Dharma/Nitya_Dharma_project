from django.apps import AppConfig


class OTPVerificationConfig(AppConfig):
    """Django app config for the isolated OTP foundation package."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "otp_verification"
    verbose_name = "OTP Verification Foundation"
