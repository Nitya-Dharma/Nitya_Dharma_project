"""
Additive email provider helpers.

Default / Gmail / Resend path remains Django's configured EMAIL_* (or Resend)
via the normal send_mail connection.

ZeptoMail is a separate, explicitly allowlisted transport. It never overwrites
EMAIL_* and never falls back to (or dual-sends with) the default provider.
"""

from __future__ import annotations

import logging
from typing import Iterable, Sequence

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import get_connection, send_mail

logger = logging.getLogger(__name__)

PROVIDER_DEFAULT = "default"
PROVIDER_ZEPTOMAIL = "zeptomail"

# Canonical flow ids for ZEPTOMAIL_ENABLED_FLOWS (comma-separated env).
FLOW_VERIFICATION = "verification"
FLOW_PASSWORD_RESET = "password_reset"
FLOW_PASSWORD_CHANGE = "password_change"
FLOW_PANDIT_ADMIN = "pandit_admin"
FLOW_LEGACY_PASSWORD_RESET = "legacy_password_reset"
FLOW_EXPERT_SET_PASSWORD = "expert_set_password"
FLOW_EXPERT_ADMIN = "expert_admin"
FLOW_EXPERT_APPROVAL = "expert_approval"
FLOW_BUREAU_APPROVAL = "bureau_approval"

KNOWN_FLOWS = frozenset(
    {
        FLOW_VERIFICATION,
        FLOW_PASSWORD_RESET,
        FLOW_PASSWORD_CHANGE,
        FLOW_PANDIT_ADMIN,
        FLOW_LEGACY_PASSWORD_RESET,
        FLOW_EXPERT_SET_PASSWORD,
        FLOW_EXPERT_ADMIN,
        FLOW_EXPERT_APPROVAL,
        FLOW_BUREAU_APPROVAL,
    }
)


def parse_zeptomail_enabled_flows(raw: str | None) -> frozenset[str]:
    """Re-export settings-safe parser for tests/callers."""
    from nityadharma.settings._zeptomail_env import (
        parse_zeptomail_enabled_flows as _parse,
    )

    return _parse(raw)


def zeptomail_settings_complete() -> bool:
    host = (getattr(settings, "ZEPTOMAIL_EMAIL_HOST", "") or "").strip()
    user = (getattr(settings, "ZEPTOMAIL_EMAIL_HOST_USER", "") or "").strip()
    password = (getattr(settings, "ZEPTOMAIL_EMAIL_HOST_PASSWORD", "") or "").strip()
    from_email = (getattr(settings, "ZEPTOMAIL_DEFAULT_FROM_EMAIL", "") or "").strip()
    return bool(host and user and password and from_email)


def resolve_provider_for_flow(flow: str | None) -> str:
    """
    Central allowlist gate.

    Missing/blank flow → default provider (existing Gmail/Resend/SMTP path).
    Flow not in ZEPTOMAIL_ENABLED_FLOWS → default.
    Flow allowlisted → zeptomail (send path still fail-closed if config incomplete).
    """
    if not flow:
        return PROVIDER_DEFAULT
    enabled = getattr(settings, "ZEPTOMAIL_ENABLED_FLOWS", None) or frozenset()
    if flow in enabled:
        return PROVIDER_ZEPTOMAIL
    return PROVIDER_DEFAULT


def _zeptomail_connection():
    if not zeptomail_settings_complete():
        raise ImproperlyConfigured(
            "ZeptoMail provider selected but ZEPTOMAIL_* settings are incomplete. "
            "Refusing to send. Default EMAIL_* / Gmail path was not used."
        )
    port = int(getattr(settings, "ZEPTOMAIL_EMAIL_PORT", 587) or 587)
    use_tls = bool(getattr(settings, "ZEPTOMAIL_EMAIL_USE_TLS", True))
    use_ssl = bool(getattr(settings, "ZEPTOMAIL_EMAIL_USE_SSL", False))
    timeout = int(getattr(settings, "ZEPTOMAIL_EMAIL_TIMEOUT", 10) or 10)
    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=settings.ZEPTOMAIL_EMAIL_HOST,
        port=port,
        username=settings.ZEPTOMAIL_EMAIL_HOST_USER,
        password=settings.ZEPTOMAIL_EMAIL_HOST_PASSWORD,
        use_tls=use_tls,
        use_ssl=use_ssl,
        timeout=timeout,
        fail_silently=False,
    )


def _assert_zeptomail_flow_authorized(flow: str | None) -> None:
    """
    ZeptoMail may only be used when central allowlisting resolves the flow
    to zeptomail. Missing, unknown, or non-allowlisted flows are refused.
    """
    if resolve_provider_for_flow(flow) != PROVIDER_ZEPTOMAIL:
        raise ImproperlyConfigured(
            "ZeptoMail requires an allowlisted flow "
            f"(got flow={flow!r}). Refusing unauthorized or missing flow; "
            "default EMAIL_* / Gmail path was not used."
        )


def send_via_provider(
    provider: str,
    subject: str,
    message: str,
    from_email: str | None,
    recipient_list: Sequence[str] | Iterable[str],
    *,
    flow: str | None = None,
    fail_silently: bool = False,
) -> int:
    """
    Send using a provider.

    ZeptoMail always requires flow= to pass central ZEPTOMAIL_ENABLED_FLOWS
    authorization. Passing provider=zeptomail alone cannot bypass the allowlist.
    Prefer send_for_flow / queue_or_send_transactional_email at call sites.
    """
    recipients = list(recipient_list)
    if provider == PROVIDER_DEFAULT:
        return send_mail(
            subject,
            message,
            from_email,
            recipients,
            fail_silently=fail_silently,
        )

    if provider == PROVIDER_ZEPTOMAIL:
        _assert_zeptomail_flow_authorized(flow)
        # Fail closed: no cross-provider fallback to Gmail/default.
        try:
            connection = _zeptomail_connection()
            zepto_from = (getattr(settings, "ZEPTOMAIL_DEFAULT_FROM_EMAIL", "") or "").strip()
            return send_mail(
                subject,
                message,
                zepto_from,
                recipients,
                connection=connection,
                fail_silently=fail_silently,
            )
        except Exception:
            if fail_silently:
                logger.exception(
                    "ZeptoMail send failed (fail_silently=True); "
                    "default provider was not used"
                )
                return 0
            raise

    raise ImproperlyConfigured(f"Unknown email provider: {provider!r}")


def send_for_flow(
    flow: str | None,
    subject: str,
    message: str,
    from_email: str | None,
    recipient_list: Sequence[str] | Iterable[str],
    *,
    fail_silently: bool = False,
) -> int:
    """Resolve provider from allowlist, then send once (no dual-send)."""
    provider = resolve_provider_for_flow(flow)
    return send_via_provider(
        provider,
        subject,
        message,
        from_email,
        recipient_list,
        flow=flow,
        fail_silently=fail_silently,
    )


def queue_or_send_transactional_email(
    flow: str,
    subject: str,
    message: str,
    from_email: str | None,
    recipient_list: Sequence[str] | Iterable[str],
    *,
    fail_silently: bool = False,
) -> int:
    """
    Celery delay with flow= (worker re-resolves allowlist), else sync send_for_flow.

    Existing contract: successful .delay() returns 1 without waiting for the worker.
    """
    from core.tasks_email import send_email_task

    recipients = list(recipient_list)
    try:
        send_email_task.delay(
            subject,
            message,
            from_email,
            recipients,
            flow=flow,
        )
        return 1
    except Exception:
        return send_for_flow(
            flow,
            subject,
            message,
            from_email,
            recipients,
            fail_silently=fail_silently,
        )
