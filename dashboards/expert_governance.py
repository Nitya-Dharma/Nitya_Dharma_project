"""Shared Expert approval/verify helpers for dashboard and Django Admin."""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse

from core.email_providers import FLOW_EXPERT_APPROVAL, queue_or_send_transactional_email


def absolute_site_url(view_name, *args, **kwargs):
    """Build absolute URL using SITE_URL + reverse (same pattern as Pandit email)."""
    site_url = getattr(settings, "SITE_URL", None)
    if not site_url:
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
        if allowed_hosts and allowed_hosts[0] != "*":
            host = allowed_hosts[0]
        else:
            host = "127.0.0.1:8000"
        protocol = "https" if getattr(settings, "USE_HTTPS", False) else "http"
        site_url = f"{protocol}://{host}"
    site_url = site_url.rstrip("/")
    relative_path = reverse(view_name, args=args, **kwargs)
    if not relative_path.startswith("/"):
        relative_path = "/" + relative_path
    return f"{site_url}{relative_path}"


def send_expert_approval_email(expert) -> None:
    """Shared expert approval email for single and bulk approve actions."""
    if not getattr(expert, "email", None):
        return
    queue_or_send_transactional_email(
        FLOW_EXPERT_APPROVAL,
        "Your Expert Profile is Approved",
        (
            "Congratulations! Your expert profile is now approved and live.\n\n"
            "You can now log in and manage your profile.\n\n"
            f"Login here: {absolute_site_url('accounts:login')}\n"
            f"Expert Dashboard: {absolute_site_url('module5_dashboards:expert_dashboard')}\n\n"
            "Thank you for joining Nitya Dharma."
        ),
        settings.DEFAULT_FROM_EMAIL,
        [expert.email],
        fail_silently=True,
    )


def approve_expert_profile(expert, *, skip_if_active: bool = False) -> bool:
    """Set is_active=True and attempt approval email.

    Returns True when approval was applied (save + email attempt).
    When skip_if_active is True and the profile is already active, returns False
    without saving or sending mail (bulk / admin duplicate protection).
    """
    if skip_if_active and getattr(expert, "is_active", False):
        return False
    expert.is_active = True
    expert.save()
    try:
        send_expert_approval_email(expert)
    except Exception:
        # Preserve existing dashboard behavior: email failures do not roll back approval.
        pass
    return True


def verify_expert_profile(expert) -> bool:
    """Set is_verified=True only. No email. Always saves (matches dashboard)."""
    expert.is_verified = True
    expert.save()
    return True
