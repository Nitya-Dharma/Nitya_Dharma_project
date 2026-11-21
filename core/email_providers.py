"""
Additive email provider helpers.

Transactional path (nine known flows):
  queue_or_send_transactional_email / send_email_task / send_for_flow
  require a known flow ID. Missing/blank/unknown flows are rejected.
  ZeptoMail is selected when the flow is in ZEPTOMAIL_ENABLED_FLOWS
  (production default = all nine). Empty allowlist is an explicit Gmail/SMTP
  rollback only — never an automatic failover when ZeptoMail fails.

Nontransactional / explicit default path:
  send_via_provider(PROVIDER_DEFAULT, ...) may be used only for explicitly
  nontransactional callers. Transactional APIs must not convert into this path
  on missing flow or ZeptoMail failure.

Celery:
  queue_or_send_transactional_email enqueues only. Broker/publish failure is
  raised (no synchronous send_for_flow fallback).

Delivery: Celery retries are at-least-once; SMTP/Celery cannot guarantee
exactly-once. Do not log recipients, passwords, tokens, or full email URLs.
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


def require_known_transactional_flow(flow: str | None) -> str:
    """Reject missing/blank/unknown transactional flow IDs."""
    if flow is None or not str(flow).strip():
        raise ImproperlyConfigured(
            "Transactional email requires a known flow id; "
            "missing/blank flow rejected. flow=None cannot select Gmail."
        )
    flow_id = str(flow).strip()
    if flow_id not in KNOWN_FLOWS:
        raise ImproperlyConfigured(
            f"Unknown transactional flow id {flow_id!r}; rejected. "
            f"Known: {', '.join(sorted(KNOWN_FLOWS))}"
        )
    return flow_id


def zeptomail_settings_complete() -> bool:
    host = (getattr(settings, "ZEPTOMAIL_EMAIL_HOST", "") or "").strip()
    user = (getattr(settings, "ZEPTOMAIL_EMAIL_HOST_USER", "") or "").strip()
    password = (getattr(settings, "ZEPTOMAIL_EMAIL_HOST_PASSWORD", "") or "").strip()
    from_email = (getattr(settings, "ZEPTOMAIL_DEFAULT_FROM_EMAIL", "") or "").strip()
    return bool(host and user and password and from_email)


def resolve_provider_for_flow(flow: str) -> str:
    """
    Resolve provider for a *known* transactional flow.

    Callers must pass a flow already validated by require_known_transactional_flow
    (or an equivalent known id). Empty ZEPTOMAIL_ENABLED_FLOWS → PROVIDER_DEFAULT
    (explicit Gmail/SMTP rollback). Allowlisted → PROVIDER_ZEPTOMAIL.
    """
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


def _assert_zeptomail_flow_authorized(flow: str) -> None:
    if resolve_provider_for_flow(flow) != PROVIDER_ZEPTOMAIL:
        raise ImproperlyConfigured(
            "ZeptoMail requires an allowlisted known flow "
            f"(got flow={flow!r}). Refusing; default EMAIL_* / Gmail was not used."
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

    PROVIDER_DEFAULT is the explicit nontransactional / rollback transport.
    PROVIDER_ZEPTOMAIL requires an allowlisted known flow and never falls back
    to Gmail on failure.
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
        flow_id = require_known_transactional_flow(flow)
        _assert_zeptomail_flow_authorized(flow_id)
        try:
            connection = _zeptomail_connection()
            zepto_from = (
                getattr(settings, "ZEPTOMAIL_DEFAULT_FROM_EMAIL", "") or ""
            ).strip()
            return send_mail(
                subject,
                message,
                zepto_from,
                recipients,
                connection=connection,
                fail_silently=fail_silently,
            )
        except Exception as exc:
            if fail_silently:
                logger.error(
                    "ZeptoMail send failed (fail_silently=True) flow=%s; "
                    "default provider was not used",
                    flow_id,
                    extra={"error_type": type(exc).__name__},
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
    """
    Transactional send: require known flow, resolve provider, send once.

    Empty allowlist → explicit Gmail/SMTP rollback for that known flow.
    ZeptoMail failure never switches to Gmail.
    """
    flow_id = require_known_transactional_flow(flow)
    provider = resolve_provider_for_flow(flow_id)
    return send_via_provider(
        provider,
        subject,
        message,
        from_email,
        recipient_list,
        flow=flow_id,
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
    Enqueue transactional email with flow= (worker re-resolves allowlist).

    Successful .delay() returns 1 without waiting for the worker.
    Broker/publish failures are raised — there is no synchronous send fallback
    (avoids duplicate or ambiguous delivery after a failed enqueue).
    fail_silently is accepted for call-site compatibility but only applies if
    enqueue raises ImproperlyConfigured for bad flow (raised before delay);
    broker errors are never swallowed.
    """
    from core.tasks_email import send_email_task

    flow_id = require_known_transactional_flow(flow)
    recipients = list(recipient_list)
    # fail_silently does not apply to enqueue: surface broker failures.
    _ = fail_silently  # retained for call-site signature compatibility
    try:
        send_email_task.delay(
            subject,
            message,
            from_email,
            recipients,
            flow=flow_id,
        )
    except Exception as exc:
        logger.error(
            "Celery enqueue failed for transactional flow=%s; "
            "no synchronous send was attempted",
            flow_id,
            extra={"error_type": type(exc).__name__},
        )
        raise
    return 1
