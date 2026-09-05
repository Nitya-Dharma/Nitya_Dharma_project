"""
Ad-attributed WhatsApp message prefill (URL content only).

Uses the existing ads_last_click_attribution session via a read-only getter.
Does not mutate session, record conversions, or change WhatsApp allowlisting.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from django.http import HttpRequest


def _safe_campaign_name(campaign_id: Optional[str]) -> Optional[str]:
    """Resolve Campaign.name from session campaign_id only; never Advertisement.campaign."""
    if campaign_id is None:
        return None
    raw = str(campaign_id).strip()
    if not raw:
        return None
    try:
        pk = int(raw)
    except (TypeError, ValueError):
        return None
    try:
        from ads.models import Campaign

        name = (
            Campaign.objects.filter(pk=pk)
            .values_list("name", flat=True)
            .first()
        )
    except Exception:
        return None
    if name is None:
        return None
    cleaned = str(name).strip()
    return cleaned or None


def build_ad_attributed_whatsapp_message(
    request: Optional[HttpRequest],
) -> Optional[str]:
    """
    Build contextual WhatsApp draft text when last-click ad attribution exists.

    Returns None when there is no ad attribution (caller keeps non-ad defaults).
    Omits Campaign/Location/Price lines when values are unavailable.
    Location and Price are intentionally omitted in this slice (no safe public
    fields on released Advertisement/Campaign).
    """
    if request is None:
        return None
    try:
        from ads_analytics.services.attribution_bridge import (
            get_last_click_attribution,
        )

        payload = get_last_click_attribution(request)
    except Exception:
        return None
    if not payload or payload.get("ad_id") is None:
        return None

    lines = [
        "NityaDharma Ad",
        "",
        "Hello! I'm interested in this advertisement",
        "and would like to know more about it.",
    ]

    campaign_name = _safe_campaign_name(payload.get("campaign_id"))
    if campaign_name:
        lines.extend(["", f"Campaign: {campaign_name}"])

    # Location / Price: no safe released Advertisement/Campaign fields — omit.

    return "\n".join(lines)


def apply_whatsapp_text_param(url: str, message: str) -> str:
    """
    Set or replace the WhatsApp `text` query parameter.

    Preserves scheme, netloc, path, fragment, and all other query params.
    Does not double-encode: `message` is plain text; encoding is applied once.
    """
    if not url or not isinstance(url, str):
        return url
    if message is None:
        return url

    parts = urlsplit(url.strip())
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    filtered = [(k, v) for (k, v) in query_items if k != "text"]
    filtered.append(("text", message))
    new_query = urlencode(filtered, quote_via=quote)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
    )
