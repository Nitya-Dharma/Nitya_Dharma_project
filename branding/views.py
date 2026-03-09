"""
Branding Management Views
Super Admin only - manage logos from dashboard.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.paginator import Paginator
from .models import BrandingLogo
from .forms import BrandingLogoUploadForm


def manage_logos(request):
    """
    Super Admin Branding Management page.
    Upload and manage logos from dashboard (not Django admin).
    """
    # Enforce Super Admin only
    if not request.user.is_authenticated or not request.user.is_superuser:
        raise Http404("Page not found")
    
    # Get all logos, ordered by creation date; Phase 8.1: paginate (20 per page)
    queryset = BrandingLogo.objects.all().order_by('-created_at')
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    all_logos = page_obj.object_list

    # Group logos by type (for current page only)
    logos_by_type = {}
    for logo in all_logos:
        logo_type = logo.get_logo_type_display()
        if logo_type not in logos_by_type:
            logos_by_type[logo_type] = []
        logos_by_type[logo_type].append(logo)
    
    # Handle logo upload
    if request.method == 'POST' and 'upload_logo' in request.POST:
        form = BrandingLogoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                logo = form.save(commit=False)
                logo.uploaded_by = request.user
                logo.save()
                messages.success(request, f'Logo "{logo.name}" uploaded successfully!')
                return redirect('branding:manage_logos')
            except Exception as e:
                messages.error(request, f'Error uploading logo: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = BrandingLogoUploadForm()
    
    return render(request, 'branding/manage_logos.html', {
        'form': form,
        'all_logos': all_logos,
        'logos_by_type': logos_by_type,
        'page_obj': page_obj,
        'user_role': 'super_admin',
        'dashboard_has_data': True,
    })


@require_http_methods(["POST"])
def activate_logo(request, logo_id):
    """
    Activate a logo (deactivates others of the same type).
    Super Admin only.
    """
    if not request.user.is_authenticated or not request.user.is_superuser:
        raise Http404("Page not found")
    
    logo = get_object_or_404(BrandingLogo, pk=logo_id)
    
    try:
        with transaction.atomic():
            # Deactivate all logos of the same type
            BrandingLogo.objects.filter(
                logo_type=logo.logo_type,
                is_active=True
            ).update(is_active=False)
            
            # Activate this logo
            logo.is_active = True
            logo.save()
        
        messages.success(request, f'Logo "{logo.name}" is now active!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Logo "{logo.name}" activated'})
        
        return redirect('branding:manage_logos')
    
    except Exception as e:
        messages.error(request, f'Error activating logo: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        return redirect('branding:manage_logos')
