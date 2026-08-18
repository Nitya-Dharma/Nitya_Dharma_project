"""Template helpers for registration OTP UI (reuse existing config gate)."""

from __future__ import annotations

from django import template

register = template.Library()


@register.simple_tag
def registration_otp_required(flow_type: str = "") -> bool:
    """True when OTP is enabled for this registration flow.

    Reuses the same gate as registration views:
    ``otp_verification.registration.factory.is_registration_otp_required``.
    """

    # Lazy import keeps templatetag module load free of app-registry side effects.
    from otp_verification.registration.factory import is_registration_otp_required

    return is_registration_otp_required(str(flow_type or "").strip())
