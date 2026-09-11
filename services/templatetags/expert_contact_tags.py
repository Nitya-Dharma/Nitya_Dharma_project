"""Template tags for Expert public contact URLs."""

from django import template

from services.expert_contact import get_expert_contact_info

register = template.Library()


@register.filter
def expert_contact_info(expert_profile):
    """
    Return call/WhatsApp contact metadata for an Expert (no request → no ad prefill).

    Prefer ad_aware_expert_contact_info when request/session attribution is needed.
    """
    if not expert_profile:
        return {
            "call_url": None,
            "whatsapp_url": None,
            "has_call": False,
            "has_whatsapp": False,
        }
    return get_expert_contact_info(expert_profile)


@register.simple_tag(takes_context=True)
def ad_aware_expert_contact_info(context, expert_profile):
    """Contact info with optional ad-attributed WhatsApp prefill from request session."""
    if not expert_profile:
        return {
            "call_url": None,
            "whatsapp_url": None,
            "has_call": False,
            "has_whatsapp": False,
        }
    request = context.get("request")
    return get_expert_contact_info(expert_profile, request=request)
