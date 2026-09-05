"""
Super Admin–only views for managing advertisement banners.

No API; standard Django forms with CSRF protection.
"""

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.db.models import Count

from .models import Advertisement, Campaign, AdSet
from .forms import AdvertisementForm, CampaignForm, AdSetForm
from .constants import AD_POSITION_IMAGE_SIZES, AD_POSITION_LABELS, get_recommended_size_text


def _super_admin_required(view_func):
    """Decorator: only is_superuser can access."""
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise Http404()
        return view_func(request, *args, **kwargs)
    return _wrapped


def _safe_int_param(raw):
    try:
        return int(raw) if raw not in (None, "") else None
    except (TypeError, ValueError):
        return None


@_super_admin_required
@require_http_methods(["GET"])
def advertisement_list(request):
    campaigns_enabled = bool(getattr(settings, "ENABLE_CAMPAIGNS", False))
    queryset = Advertisement.objects.select_related("campaign", "ad_set").order_by(
        "-created_at"
    )
    filter_campaign = None
    filter_ad_set = None
    campaign_id = _safe_int_param(request.GET.get("campaign_id"))
    ad_set_id = _safe_int_param(request.GET.get("ad_set_id"))
    if campaigns_enabled and campaign_id is not None:
        queryset = queryset.filter(campaign_id=campaign_id)
        filter_campaign = Campaign.objects.filter(pk=campaign_id).first()
    if campaigns_enabled and ad_set_id is not None:
        queryset = queryset.filter(ad_set_id=ad_set_id)
        filter_ad_set = AdSet.objects.select_related("campaign").filter(pk=ad_set_id).first()
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    context = {
        "advertisements": page_obj.object_list,
        "page_obj": page_obj,
        "dashboard_has_data": True,
        "campaigns_enabled": campaigns_enabled,
        "filter_campaign": filter_campaign,
        "filter_ad_set": filter_ad_set,
        "filter_campaign_id": str(campaign_id) if campaign_id is not None else "",
        "filter_ad_set_id": str(ad_set_id) if ad_set_id is not None else "",
    }
    if campaigns_enabled:
        context["campaign_filter_choices"] = Campaign.objects.order_by("-created_at")
        adset_qs = AdSet.objects.select_related("campaign").order_by("-created_at")
        if campaign_id is not None:
            adset_qs = adset_qs.filter(campaign_id=campaign_id)
        context["adset_filter_choices"] = adset_qs
    return render(request, "ads/advertisement_list.html", context)


@_super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def advertisement_create(request):
    campaigns_enabled = bool(getattr(settings, "ENABLE_CAMPAIGNS", False))
    initial = {}
    if campaigns_enabled:
        cid = _safe_int_param(request.GET.get("campaign_id"))
        aid = _safe_int_param(request.GET.get("ad_set_id"))
        if cid is not None:
            initial["campaign"] = cid
        if aid is not None:
            initial["ad_set"] = aid
    if request.method == "POST":
        form = AdvertisementForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Advertisement created successfully.")
            return redirect("ads:advertisement_list")
    else:
        form = AdvertisementForm(initial=initial)
    placement_upload_choices = [
        (slot, label, form[Advertisement.SLOT_IMAGE_FIELDS[slot]], get_recommended_size_text(slot))
        for slot, label in Advertisement.PLACEMENT_CHOICES
    ]
    return render(
        request,
        "ads/advertisement_form.html",
        {
            "form": form,
            "title": "Create Advertisement",
            "dashboard_has_data": True,
            "campaigns_enabled": campaigns_enabled,
            "position_sizes": AD_POSITION_IMAGE_SIZES,
            "position_labels": AD_POSITION_LABELS,
            "placement_choices": Advertisement.PLACEMENT_CHOICES,
            "placement_upload_choices": placement_upload_choices,
            "get_recommended_size_text": get_recommended_size_text,
            "slot_image_field_names": list(Advertisement.SLOT_IMAGE_FIELDS.values()),
        },
    )


@_super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def advertisement_edit(request, pk):
    campaigns_enabled = bool(getattr(settings, "ENABLE_CAMPAIGNS", False))
    ad = get_object_or_404(Advertisement.objects.select_related("campaign", "ad_set"), pk=pk)
    if request.method == "POST":
        form = AdvertisementForm(request.POST, request.FILES, instance=ad)
        if form.is_valid():
            form.save()
            messages.success(request, "Advertisement updated successfully.")
            return redirect("ads:advertisement_list")
    else:
        form = AdvertisementForm(instance=ad)
    placement_upload_choices = [
        (slot, label, form[Advertisement.SLOT_IMAGE_FIELDS[slot]], get_recommended_size_text(slot))
        for slot, label in Advertisement.PLACEMENT_CHOICES
    ]
    return render(
        request,
        "ads/advertisement_form.html",
        {
            "form": form,
            "ad": ad,
            "title": "Edit Advertisement",
            "dashboard_has_data": True,
            "campaigns_enabled": campaigns_enabled,
            "position_sizes": AD_POSITION_IMAGE_SIZES,
            "position_labels": AD_POSITION_LABELS,
            "placement_choices": Advertisement.PLACEMENT_CHOICES,
            "placement_upload_choices": placement_upload_choices,
            "get_recommended_size_text": get_recommended_size_text,
            "slot_image_field_names": list(Advertisement.SLOT_IMAGE_FIELDS.values()),
        },
    )


@_super_admin_required
@csrf_protect
@require_http_methods(["POST"])
def advertisement_toggle(request, pk):
    ad = get_object_or_404(Advertisement, pk=pk)
    ad.is_active = not ad.is_active
    ad.save()
    status = 'active' if ad.is_active else 'inactive'
    messages.success(request, f'Advertisement is now {status}.')
    return redirect('ads:advertisement_list')


@_super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def advertisement_delete(request, pk):
    ad = get_object_or_404(Advertisement, pk=pk)
    if request.method == 'POST':
        ad.delete()
        messages.success(request, 'Advertisement deleted.')
        return redirect('ads:advertisement_list')
    return render(request, 'ads/advertisement_confirm_delete.html', {
        'ad': ad,
        'dashboard_has_data': True,
    })


@_super_admin_required
@require_http_methods(["GET"])
def campaign_list(request):
    if not bool(getattr(settings, "ENABLE_CAMPAIGNS", False)):
        messages.info(request, "Campaign feature is disabled.")
        return redirect("ads:advertisement_list")
    queryset = Campaign.objects.annotate(ad_count=Count("advertisements")).order_by(
        "-priority", "-created_at"
    )
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    campaigns = list(page_obj.object_list)
    days = max(1, min(365, int(request.GET.get("days", 30))))
    try:
        from ads_analytics.services.dashboard_service import (
            get_campaign_conversion_metrics,
            get_campaign_delivery_metrics,
        )

        for campaign in campaigns:
            cid = str(campaign.pk)
            campaign.conversion_metrics = get_campaign_conversion_metrics(
                cid,
                days=days,
            )
            campaign.delivery_metrics = get_campaign_delivery_metrics(
                cid,
                days=days,
            )
    except Exception:
        for campaign in campaigns:
            campaign.conversion_metrics = {
                "conversion_count": 0,
                "booking_intent_count": 0,
                "other_count": 0,
                "profile_view_count": 0,
            }
            campaign.delivery_metrics = {
                "impressions": 0,
                "clicks": 0,
                "ctr": 0.0,
            }
    return render(
        request,
        "ads/campaign_list.html",
        {
            "campaigns": campaigns,
            "page_obj": page_obj,
            "dashboard_has_data": True,
            "campaigns_enabled": True,
        },
    )


@_super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def campaign_create(request):
    if not bool(getattr(settings, "ENABLE_CAMPAIGNS", False)):
        messages.info(request, "Campaign feature is disabled.")
        return redirect("ads:advertisement_list")
    if request.method == "POST":
        form = CampaignForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Campaign created successfully.")
            return redirect("ads:campaign_list")
    else:
        form = CampaignForm()
    return render(
        request,
        "ads/campaign_form.html",
        {
            "form": form,
            "title": "Create Campaign",
            "dashboard_has_data": True,
            "campaigns_enabled": True,
        },
    )


@_super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def campaign_edit(request, pk):
    if not bool(getattr(settings, "ENABLE_CAMPAIGNS", False)):
        messages.info(request, "Campaign feature is disabled.")
        return redirect("ads:advertisement_list")
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == "POST":
        form = CampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, "Campaign updated successfully.")
            return redirect("ads:campaign_list")
    else:
        form = CampaignForm(instance=campaign)
    return render(
        request,
        "ads/campaign_form.html",
        {
            "form": form,
            "campaign": campaign,
            "title": "Edit Campaign",
            "dashboard_has_data": True,
            "campaigns_enabled": True,
        },
    )


@_super_admin_required
@csrf_protect
@require_http_methods(["POST"])
def campaign_toggle(request, pk):
    if not bool(getattr(settings, "ENABLE_CAMPAIGNS", False)):
        messages.info(request, "Campaign feature is disabled.")
        return redirect("ads:advertisement_list")
    campaign = get_object_or_404(Campaign, pk=pk)
    current = str(campaign.status or "").upper()
    if current == Campaign.STATUS_ACTIVE:
        campaign.status = Campaign.STATUS_PAUSED
    else:
        campaign.status = Campaign.STATUS_ACTIVE
    campaign.save(update_fields=["status"])
    messages.success(request, f"Campaign is now {campaign.status.lower()}.")
    return redirect("ads:campaign_list")


@_super_admin_required
@require_http_methods(["GET"])
def adset_list(request):
    if not bool(getattr(settings, "ENABLE_CAMPAIGNS", False)):
        messages.info(request, "Campaign feature is disabled.")
        return redirect("ads:advertisement_list")
    campaign_id = _safe_int_param(request.GET.get("campaign_id"))
    qs = AdSet.objects.select_related("campaign").order_by("-created_at")
    filter_campaign = None
    if campaign_id is not None:
        qs = qs.filter(campaign_id=campaign_id)
        filter_campaign = Campaign.objects.filter(pk=campaign_id).first()
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    return render(
        request,
        "ads/adset_list.html",
        {
            "adsets": page_obj.object_list,
            "page_obj": page_obj,
            "filter_campaign": filter_campaign,
            "filter_campaign_id": str(campaign_id) if campaign_id is not None else "",
            "dashboard_has_data": True,
            "campaigns_enabled": True,
        },
    )


@_super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def adset_create(request):
    if not bool(getattr(settings, "ENABLE_CAMPAIGNS", False)):
        messages.info(request, "Campaign feature is disabled.")
        return redirect("ads:advertisement_list")
    initial = {}
    cid = _safe_int_param(request.GET.get("campaign_id"))
    if cid is not None:
        initial["campaign"] = cid
    if request.method == "POST":
        form = AdSetForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ad set created successfully.")
            return redirect("ads:adset_list")
    else:
        form = AdSetForm(initial=initial)
    return render(
        request,
        "ads/adset_form.html",
        {
            "form": form,
            "title": "Create Ad Set",
            "dashboard_has_data": True,
            "campaigns_enabled": True,
        },
    )


@_super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def adset_edit(request, pk):
    if not bool(getattr(settings, "ENABLE_CAMPAIGNS", False)):
        messages.info(request, "Campaign feature is disabled.")
        return redirect("ads:advertisement_list")
    adset = get_object_or_404(AdSet.objects.select_related("campaign"), pk=pk)
    if request.method == "POST":
        form = AdSetForm(request.POST, instance=adset)
        if form.is_valid():
            form.save()
            messages.success(request, "Ad set updated successfully.")
            return redirect("ads:adset_list")
    else:
        form = AdSetForm(instance=adset)
    return render(
        request,
        "ads/adset_form.html",
        {
            "form": form,
            "adset": adset,
            "title": "Edit Ad Set",
            "dashboard_has_data": True,
            "campaigns_enabled": True,
        },
    )


@_super_admin_required
@csrf_protect
@require_http_methods(["POST"])
def adset_toggle(request, pk):
    if not bool(getattr(settings, "ENABLE_CAMPAIGNS", False)):
        messages.info(request, "Campaign feature is disabled.")
        return redirect("ads:advertisement_list")
    adset = get_object_or_404(AdSet, pk=pk)
    adset.is_active = not adset.is_active
    adset.save(update_fields=["is_active"])
    status = "active" if adset.is_active else "inactive"
    messages.success(request, f"Ad set is now {status}.")
    return redirect("ads:adset_list")
