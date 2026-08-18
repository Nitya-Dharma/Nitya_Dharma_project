"""Expert-only public contact helpers without WhatsApp verification dependencies."""

from __future__ import annotations

from accounts.phone_utils import normalize_phone_number


def get_expert_call_url(expert_profile) -> str | None:
    """Return a tel: URL for active Experts with a usable phone value."""
    if not expert_profile or not getattr(expert_profile, "is_active", False):
        return None

    phone = str(getattr(expert_profile, "phone", "") or "").strip()
    if len(phone) <= 5:
        return None
    return f"tel:{phone}"


def get_expert_whatsapp_url(expert_profile) -> str | None:
    """Return a direct wa.me URL for active Experts with a normalizable phone."""
    if not expert_profile or not getattr(expert_profile, "is_active", False):
        return None

    normalized_phone = normalize_phone_number(getattr(expert_profile, "phone", None))
    if not normalized_phone:
        return None
    return f"https://wa.me/{normalized_phone}"


def get_expert_contact_info(expert_profile) -> dict[str, object]:
    """Return public-safe Expert contact metadata for future template use."""
    call_url = get_expert_call_url(expert_profile)
    whatsapp_url = get_expert_whatsapp_url(expert_profile)
    return {
        "call_url": call_url,
        "whatsapp_url": whatsapp_url,
        "has_call": call_url is not None,
        "has_whatsapp": whatsapp_url is not None,
    }
