"""
Branding Management Views
Super Admin only - manage logos from dashboard.
"""
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.paginator import Paginator
from django.conf import settings
from PIL import Image, ImageOps
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


def manifest_json(request):
    """
    Dynamic PWA manifest using active branding favicon when available.
    """
    active_favicon_logo = BrandingLogo.objects.filter(
        logo_type='favicon',
        is_active=True,
    ).first()
    active_navbar_logo = BrandingLogo.objects.filter(
        logo_type='navbar_logo',
        is_active=True,
    ).first()

    icon_url = '/static/pwa/icons/icon-192.png'
    if active_favicon_logo:
        if active_favicon_logo.favicon_image:
            icon_url = active_favicon_logo.favicon_image.url
        elif active_favicon_logo.logo_image:
            icon_url = active_favicon_logo.logo_image.url
    elif active_navbar_logo and active_navbar_logo.logo_image:
        # Safe fallback: use current active navbar branding logo.
        icon_url = active_navbar_logo.logo_image.url

    generated_icons = _build_manifest_icons(icon_url)

    response = JsonResponse({
        "name": "Nitya Dharma",
        "short_name": "Nitya Dharma",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#c62828",
        "icons": generated_icons
    })
    # Prevent stale manifest/icon caching in browsers after admin updates.
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


def _build_manifest_icons(icon_url):
    """
    Build installable square app icons (192 and 512) from selected branding image.
    Falls back to static defaults if generation fails.
    """
    if not icon_url.startswith(settings.MEDIA_URL):
        return [
            {"src": "/static/pwa/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/static/pwa/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        ]

    relative_media_path = icon_url.replace(settings.MEDIA_URL, "", 1).lstrip("/")
    source_path = Path(settings.MEDIA_ROOT) / relative_media_path
    if not source_path.exists():
        return [
            {"src": "/static/pwa/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/static/pwa/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        ]

    out_dir = Path(settings.MEDIA_ROOT) / "branding" / "pwa_icons"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = str(int(source_path.stat().st_mtime))

    icons = []
    for size in (192, 512):
        out_name = f"app-icon-{size}-{stamp}.png"
        out_path = out_dir / out_name
        if not out_path.exists():
            with Image.open(source_path) as img:
                # Center-crop and resize to required square icon size.
                square = ImageOps.fit(img.convert("RGBA"), (size, size), method=Image.Resampling.LANCZOS)
                square.save(out_path, format="PNG", optimize=True)
        icons.append({
            "src": f"{settings.MEDIA_URL}branding/pwa_icons/{out_name}",
            "sizes": f"{size}x{size}",
            "type": "image/png",
            "purpose": "any"
        })
    return icons
