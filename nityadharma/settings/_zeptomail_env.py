"""Settings-safe helpers for additive ZeptoMail env parsing (no Django imports)."""

from __future__ import annotations

# Canonical nine transactional flow IDs (must match core.email_providers.KNOWN_FLOWS).
KNOWN_TRANSACTIONAL_FLOW_IDS = frozenset(
    {
        "verification",
        "password_reset",
        "password_change",
        "pandit_admin",
        "legacy_password_reset",
        "expert_set_password",
        "expert_admin",
        "expert_approval",
        "bureau_approval",
    }
)

# Release-primary default: all nine flows. Rollback = set ZEPTOMAIL_ENABLED_FLOWS empty.
DEFAULT_RELEASE_ZEPTOMAIL_ENABLED_FLOWS = (
    "verification,password_reset,password_change,pandit_admin,"
    "legacy_password_reset,expert_set_password,expert_admin,"
    "expert_approval,bureau_approval"
)


class UnknownTransactionalFlowId(ValueError):
    """Raised when ZEPTOMAIL_ENABLED_FLOWS contains an unknown flow id."""


def parse_zeptomail_enabled_flows(raw: str | None) -> frozenset[str]:
    """Parse comma-separated allowlist; empty/blank → no ZeptoMail traffic (Gmail rollback).

    Unknown flow IDs are rejected (fail closed at settings parse time).
    """
    if not raw:
        return frozenset()
    parts = [part.strip() for part in str(raw).split(",") if part.strip()]
    if not parts:
        return frozenset()
    unknown = sorted({p for p in parts if p not in KNOWN_TRANSACTIONAL_FLOW_IDS})
    if unknown:
        raise UnknownTransactionalFlowId(
            "ZEPTOMAIL_ENABLED_FLOWS contains unknown flow id(s): "
            + ", ".join(unknown)
            + ". Known ids: "
            + ", ".join(sorted(KNOWN_TRANSACTIONAL_FLOW_IDS))
        )
    return frozenset(parts)
