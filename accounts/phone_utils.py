"""Phone normalization helpers for accounts registration / verification."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def normalize_phone_number(phone: str | None) -> str | None:
    """Normalize Indian mobiles to 91XXXXXXXXXX. Returns None if invalid."""

    phone = str(phone or "").strip()
    phone = "".join(filter(str.isdigit, phone))

    if phone.startswith("91") and len(phone) == 12:
        return phone
    if len(phone) == 10:
        return "91" + phone
    return None


def phone_already_registered(
    normalized_phone: str,
    *,
    exclude_user_id: int | None = None,
) -> bool:
    """Return True when another user already owns this normalized phone.

    NOTE (DB integrity recommendation, not auto-applied):
    Consider a UniqueConstraint / unique=True on User.phone_number after
    cleaning legacy duplicates. Do not apply that migration without approval.
    """

    from accounts.models import User

    if not normalized_phone:
        return False
    candidates = {normalized_phone}
    if normalized_phone.startswith("91") and len(normalized_phone) == 12:
        candidates.add(normalized_phone[2:])
    qs = User.objects.filter(phone_number__in=candidates)
    if exclude_user_id is not None:
        qs = qs.exclude(pk=exclude_user_id)
    exists = qs.exists()
    if exists:
        logger.warning(
            "Duplicate phone registration blocked",
            extra={
                "normalized_phone": normalized_phone,
                "exclude_user_id": exclude_user_id,
            },
        )
    return exists
