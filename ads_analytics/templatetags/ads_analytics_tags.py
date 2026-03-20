"""
Template tags for ad analytics. Use in ad unit partial to record impressions.
Does not alter ad content or placement.
"""

from django import template
from django.template.base import Node

register = template.Library()


class RecordAdImpressionNode(Node):
    def __init__(self, ad_var, slot_var, request_var, page_type_var):
        self.ad_var = template.Variable(ad_var)
        self.slot_var = template.Variable(slot_var)
        self.request_var = template.Variable(request_var)
        self.page_type_var = template.Variable(page_type_var) if page_type_var else None

    def render(self, context):
        try:
            ad = self.ad_var.resolve(context)
            slot = self.slot_var.resolve(context)
            request = self.request_var.resolve(context)
            page_type = self.page_type_var.resolve(context) if self.page_type_var else ""
        except template.VariableDoesNotExist:
            return ""
        if not ad or not getattr(ad, "pk", None):
            return ""
        from ads_analytics.services import record_ad_impression

        user_id = request.user.pk if getattr(request, "user", None) and request.user.is_authenticated else None
        record_ad_impression(
            ad_id=ad.pk,
            placement_position=str(slot),
            page_type=page_type or _page_type_from_path(getattr(request, "path", "")),
            page_url=getattr(request, "build_absolute_uri", lambda: "")() or "",
            user_id=user_id,
            pandit_id=getattr(context.get("pandit"), "pk", None) or getattr(context.get("profile"), "pk", None),
            request=request,
        )
        return ""


def _page_type_from_path(path):
    if not path:
        return ""
    if path == "/" or path.startswith("/home"):
        return "homepage"
    if "/search" in path or "/pooja" in path:
        return "search"
    if "/dashboard" in path:
        return "dashboard"
    if "/pandit" in path or "/profile" in path:
        return "pandit_profile"
    if "/feed" in path:
        return "feed"
    return "other"


@register.tag(name="record_ad_impression")
def do_record_ad_impression(parser, token):
    """Usage: {% record_ad_impression ad slot request page_type %} or {% record_ad_impression ad slot request %}"""
    bits = token.split_contents()
    if len(bits) < 4:
        raise template.TemplateSyntaxError("Usage: {% record_ad_impression ad slot request [page_type] %}")
    page_type = bits[4] if len(bits) > 4 else None
    return RecordAdImpressionNode(bits[1], bits[2], bits[3], page_type)
