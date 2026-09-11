"""Expert-only public contact helpers without WhatsApp verification dependencies."""

from __future__ import annotations

from typing import Optional

from django.http import HttpRequest

from accounts.phone_utils import normalize_phone_number


def get_expert_call_url(expert_profile) -> str | None:
    """Return a tel: URL for active Experts with a usable phone value."""
    if not expert_profile or not getattr(expert_profile, "is_active", False):
        return None

    phone = str(getattr(expert_profile, "phone", "") or "").strip()
    if len(phone) <= 5:
        return None
    return f"tel:{phone}"


def get_expert_whatsapp_url(
    expert_profile,
    request: Optional[HttpRequest] = None,
) -> str | None:
    """
    Return a wa.me URL for active Experts with a normalizable phone.

    When ``request`` is provided and last-click Ads attribution exists,
    enrich with the existing ad-attributed WhatsApp prefill (Batch B).
    Non-ad callers (no request / no session attribution) keep bare wa.me.
    """
    if not expert_profile or not getattr(expert_profile, "is_active", False):
        return None

    normalized_phone = normalize_phone_number(getattr(expert_profile, "phone", None))
    if not normalized_phone:
        return None

    url = f"https://wa.me/{normalized_phone}"
    if request is None:
        return url

    try:
        from profiles.whatsapp_ad_prefill import (
            apply_whatsapp_text_param,
            build_ad_attributed_whatsapp_message,
        )

        attributed = build_ad_attributed_whatsapp_message(request)
        if attributed:
            return apply_whatsapp_text_param(url, attributed)
    except Exception:
        pass
    return url


def get_expert_contact_info(
    expert_profile,
    request: Optional[HttpRequest] = None,
) -> dict[str, object]:
    """Return public-safe Expert contact metadata for template use."""
    call_url = get_expert_call_url(expert_profile)
    whatsapp_url = get_expert_whatsapp_url(expert_profile, request=request)
    return {
        "call_url": call_url,
        "whatsapp_url": whatsapp_url,
        "has_call": call_url is not None,
        "has_whatsapp": whatsapp_url is not None,
    }
