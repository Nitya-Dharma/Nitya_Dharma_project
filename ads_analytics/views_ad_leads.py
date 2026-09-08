"""Super Admin Ads Lead list and status update.

List GET is read-only. Status mutation is POST-only and does not record
analytics, attribution, WhatsApp, or booking events.
"""

from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods

from ads.views import _super_admin_required
from ads_analytics.models import AdLead

PAGE_SIZE = 20


def _status_choices():
    return list(AdLead._meta.get_field("status").choices)


def _valid_status_values():
    return {value for value, _label in _status_choices()}


@_super_admin_required
@require_GET
def ad_lead_list(request):
    queryset = AdLead.objects.select_related(
        "advertisement",
        "source_conversion",
        "user",
    ).order_by("-created_at", "-id")
    page_obj = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "ads_analytics/ad_lead_list.html",
        {
            "page_obj": page_obj,
            "leads": page_obj.object_list,
            "status_choices": _status_choices(),
            "dashboard_has_data": True,
        },
    )


@_super_admin_required
@csrf_protect
@require_http_methods(["POST"])
def update_ad_lead_status(request, lead_id):
    lead = get_object_or_404(AdLead, pk=lead_id)
    submitted = request.POST.get("status")
    if submitted not in _valid_status_values():
        return HttpResponseBadRequest("Invalid status.")
    lead.status = submitted
    lead.save(update_fields=["status", "updated_at"])
    return redirect("ads_leads:ad_lead_list")
