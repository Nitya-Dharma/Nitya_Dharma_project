"""URL routes for registration OTP send, verification, and resend."""

from django.urls import path

from otp_verification.registration.views import (
    resend_registration_otp,
    send_registration_otp,
    verify_registration_otp,
)

app_name = "otp_verification"

urlpatterns = [
    path(
        "registration/send/",
        send_registration_otp,
        name="send_registration_otp",
    ),
    path(
        "registration/verify/",
        verify_registration_otp,
        name="verify_registration_otp",
    ),
    path(
        "registration/resend/",
        resend_registration_otp,
        name="resend_registration_otp",
    ),
]

