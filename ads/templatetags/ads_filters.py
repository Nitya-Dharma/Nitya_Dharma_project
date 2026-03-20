"""Template filters for ads app."""
from django import template

register = template.Library()


@register.filter
def ad_image_for_slot(ad, slot):
    """Return the image to display for this ad in the given slot (per-slot or legacy)."""
    if not ad:
        return None
    if slot:
        return ad.get_image_for_slot(slot)
    return getattr(ad, 'image', None)
