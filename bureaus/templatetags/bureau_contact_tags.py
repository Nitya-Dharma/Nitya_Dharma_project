"""Template tags for Bureau public contact URLs (wrap existing helpers only)."""

from django import template

from bureaus.whatsapp_contact import get_bureau_whatsapp_url

register = template.Library()


@register.simple_tag(takes_context=True)
def bureau_whatsapp_url(context, bureau):
    """
    Build bureau WhatsApp CTA URL via get_bureau_whatsapp_url.

    Uses stored whatsapp_number only; optional ad prefill when request is present.
    Returns None when no number is configured.
    """
    if not bureau:
        return None
    request = context.get("request")
    return get_bureau_whatsapp_url(
        getattr(bureau, "whatsapp_number", None),
        request=request,
    )
