"""Bureau public WhatsApp URL helper (Ads prefill only; no number mutation)."""

from __future__ import annotations

from typing import Optional

from django.http import HttpRequest


def get_bureau_whatsapp_url(
    whatsapp_number,
    request: Optional[HttpRequest] = None,
) -> str | None:
    """
    Build a wa.me URL from the stored Bureau WhatsApp value as-is.

    Does not normalize or rewrite the stored number. When ``request`` is
    provided and last-click Ads attribution exists, enrich with the existing
    ad-attributed WhatsApp prefill. Non-ad callers keep bare wa.me.
    """
    raw = str(whatsapp_number or "").strip()
    if not raw:
        return None

    url = f"https://wa.me/{raw}"
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
