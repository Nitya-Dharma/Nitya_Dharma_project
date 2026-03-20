"""
Super Admin–only views for managing advertisement banners.

No API; standard Django forms with CSRF protection.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator

from .models import Advertisement
from .forms import AdvertisementForm
from .constants import AD_POSITION_IMAGE_SIZES, AD_POSITION_LABELS, get_recommended_size_text


def _super_admin_required(view_func):
    """Decorator: only is_superuser can access."""
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise Http404()
        return view_func(request, *args, **kwargs)
    return _wrapped


@_super_admin_required
@require_http_methods(["GET"])
def advertisement_list(request):
    queryset = Advertisement.objects.all().order_by('-created_at')
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'ads/advertisement_list.html', {
        'advertisements': page_obj.object_list,
        'page_obj': page_obj,
        'dashboard_has_data': True,  # Always show our content (we render our own empty state)
    })


@_super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def advertisement_create(request):
    if request.method == 'POST':
        form = AdvertisementForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Advertisement created successfully.')
            return redirect('ads:advertisement_list')
    else:
        form = AdvertisementForm()
    placement_upload_choices = [
        (slot, label, form[Advertisement.SLOT_IMAGE_FIELDS[slot]], get_recommended_size_text(slot))
        for slot, label in Advertisement.PLACEMENT_CHOICES
    ]
    return render(request, 'ads/advertisement_form.html', {
        'form': form,
        'title': 'Create Advertisement',
        'dashboard_has_data': True,
        'position_sizes': AD_POSITION_IMAGE_SIZES,
        'position_labels': AD_POSITION_LABELS,
        'placement_choices': Advertisement.PLACEMENT_CHOICES,
        'placement_upload_choices': placement_upload_choices,
        'get_recommended_size_text': get_recommended_size_text,
        'slot_image_field_names': list(Advertisement.SLOT_IMAGE_FIELDS.values()),
    })


@_super_admin_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def advertisement_edit(request, pk):
    ad = get_object_or_404(Advertisement, pk=pk)
    if request.method == 'POST':
        form = AdvertisementForm(request.POST, request.FILES, instance=ad)
        if form.is_valid():
            form.save()
            messages.success(request, 'Advertisement updated successfully.')
            return redirect('ads:advertisement_list')
    else:
        form = AdvertisementForm(instance=ad)
    placement_upload_choices = [
        (slot, label, form[Advertisement.SLOT_IMAGE_FIELDS[slot]], get_recommended_size_text(slot))
        for slot, label in Advertisement.PLACEMENT_CHOICES
    ]
    return render(request, 'ads/advertisement_form.html', {
        'form': form,
        'ad': ad,
        'title': 'Edit Advertisement',
        'dashboard_has_data': True,
        'position_sizes': AD_POSITION_IMAGE_SIZES,
        'position_labels': AD_POSITION_LABELS,
        'placement_choices': Advertisement.PLACEMENT_CHOICES,
        'placement_upload_choices': placement_upload_choices,
        'get_recommended_size_text': get_recommended_size_text,
        'slot_image_field_names': list(Advertisement.SLOT_IMAGE_FIELDS.values()),
    })


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
