"""
Pages views for page management.

Security Rules:
- Public pages: Access controlled by selectors
- Page management: Only accessible by page owner or admin
- All views use public_id (UUIDv7) to prevent enumeration attacks
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.core.exceptions import PermissionDenied, ValidationError
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from core.public_id import resolve_public_id, reject_bigint_id
from .models import Page, PageGalleryImage, PagePost, PageReview, PageRole
from seo.schema_builders import build_page_schema
from .services import create_page, deactivate_page, activate_page, make_page_invisible, make_page_visible
from .selectors import get_page_by_public_id, list_pages_for_admin_pandit, list_pages_for_super_admin
from .page_permissions import (
    is_page_owner, is_page_moderator, has_page_role, is_super_admin,
    can_edit_page_media, can_manage_visibility, can_edit_page_slug,
    can_upload_gallery,
    can_assign_moderator, get_user_page_role, get_pages_for_user,
    can_create_post
)
from .constants import (
    PAGE_TYPE_TEMPLE,
    PAGE_TYPE_BRAND,
    PAGE_TYPE_TRUST,
    PAGE_TYPE_SOCIAL_SERVICE,
    PAGE_STATUS_ACTIVE,
    PAGE_STATUS_DEACTIVATED,
    PAGE_STATUS_INVISIBLE,
)
# Helper functions defined below
from engagement.services import record_view
from engagement.constants import ENTITY_TEMPLE_PAGE
import logging

logger = logging.getLogger(__name__)


def _is_admin_pandit(user):
    """Check if user is Admin Pandit."""
    return user and user.is_authenticated and user.role == 'admin' and not user.is_superuser


def _is_super_admin(user):
    """Check if user is Super Admin."""
    return user and user.is_authenticated and user.is_superuser


@login_required
def page_create(request):
    """
    Create a new page.
    
    Rules:
    - Admin Pandit: Can create ONLY Temple pages
    - Super Admin: Can create all page types
    - End Users: No access
    """
    from .forms import PageCreateForm
    from masterdata.models import City
    
    # Determine allowed page types based on user role
    if _is_super_admin(request.user):
        allowed_page_types = [PAGE_TYPE_TEMPLE, PAGE_TYPE_BRAND, PAGE_TYPE_TRUST, PAGE_TYPE_SOCIAL_SERVICE]
    elif _is_admin_pandit(request.user):
        allowed_page_types = [PAGE_TYPE_TEMPLE]
    else:
        messages.error(request, "You do not have permission to create pages.")
        return redirect('pages:page_list')
    
    if request.method == 'POST':
        form = PageCreateForm(request.POST, request.FILES, allowed_page_types=allowed_page_types)
        if form.is_valid():
            try:
                # Create page using service (handles permissions and audit)
                slug_value = form.cleaned_data.get('slug')
                slug_value = (slug_value or '').strip() or None
                # Extract city and area IDs (form returns objects, but service expects IDs)
                city_obj = form.cleaned_data.get('city')
                city_id = city_obj.id if city_obj else None
                area_obj = form.cleaned_data.get('area')
                area_id = area_obj.id if area_obj else None
                
                payload = {
                    'title': form.cleaned_data['title'],
                    'slug': slug_value,
                    'description': form.cleaned_data.get('description', ''),
                    'address': form.cleaned_data.get('address', ''),
                    'city': city_id,  # Pass ID, not object
                    'area': area_id,   # Pass ID, not object
                    'profile_image': request.FILES.get('profile_image'),
                    'cover_image': request.FILES.get('cover_image'),
                }
                page = create_page(
                    user=request.user,
                    page_type=form.cleaned_data['page_type'],
                    payload=payload
                )
                
                # Handle SEO fields after page creation
                seo_edited = False
                if 'seo_title' in form.cleaned_data:
                    seo_title = form.cleaned_data.get('seo_title')
                    if seo_title:
                        seo_title = seo_title.strip()
                        if seo_title:
                            if len(seo_title) > 60:
                                messages.warning(request, 'SEO title truncated to 60 characters.')
                            page.seo_title = seo_title[:60]
                            seo_edited = True
                
                if 'seo_description' in form.cleaned_data:
                    seo_description = form.cleaned_data.get('seo_description')
                    if seo_description:
                        seo_description = seo_description.strip()
                        if seo_description:
                            if len(seo_description) > 160:
                                messages.warning(request, 'SEO description truncated to 160 characters.')
                            page.seo_description = seo_description[:160]
                            seo_edited = True
                
                if 'seo_keywords' in form.cleaned_data:
                    seo_keywords = form.cleaned_data.get('seo_keywords')
                    if seo_keywords:
                        seo_keywords = seo_keywords.strip()
                        if seo_keywords:
                            page.seo_keywords = seo_keywords
                        seo_edited = True
                
                # Mark SEO as manually edited if user provided any SEO data
                if seo_edited:
                    page.seo_autogenerated = False
                else:
                    # Auto-generate SEO if not provided (form.save() would do this, but we use service)
                    from .seo_services import auto_generate_page_seo
                    auto_generate_page_seo(page, force=True)
                
                # Save SEO fields using update() to avoid triggering full_clean() validation
                # This bypasses model validation which would check owner_role and other fields
                from django.utils import timezone
                from .models import Page
                Page.objects.filter(pk=page.pk).update(
                    seo_title=page.seo_title,
                    seo_description=page.seo_description,
                    seo_keywords=page.seo_keywords,
                    seo_autogenerated=page.seo_autogenerated,
                    seo_last_updated_at=timezone.now()
                )
                # Refresh instance to get updated values
                page.refresh_from_db()
                
                messages.success(request, f"Page '{page.title}' created successfully!")
                return redirect('pages:page_detail', page_public_id=page.public_id)
            except Exception as e:
                logger.error(f"Error creating page: {str(e)}", exc_info=True)
                messages.error(request, f"Error creating page: {str(e)}")
        else:
            # Only show error message if there are actual form errors
            if form.errors:
                messages.error(request, "Please correct the errors below.")
    else:
        form = PageCreateForm(allowed_page_types=allowed_page_types)
    
    # Get cities for dropdown
    cities = City.objects.filter(is_active=True).order_by('name')
    
    context = {
        'form': form,
        'cities': cities,
        'allowed_page_types': allowed_page_types,  # Pass to template for page type dropdown
    }
    return render(request, 'pages/page_create.html', context)



    """
    Display page detail view.
    
    Supports both SEO slug and public_id (UUIDv7) for backward compatibility.
    
    Rules:
    - Public pages visible to all
    - INVISIBLE pages still accessible via direct URL
    - DEACTIVATED pages show banner
    - HIDDEN pages visible to admins only
    """
    

def page_detail(request, page_public_id):

    page = Page.objects.filter(slug=page_public_id).first()

    if not page:
        page = Page.objects.filter(public_id=page_public_id).first()

    if not page:
        raise Http404("Page not found")

    
    
    # Check visibility rules
    show_banner = False
    banner_message = None
    
    if page.status == PAGE_STATUS_INVISIBLE:
        # INVISIBLE pages still accessible via direct URL
        show_banner = True
        banner_message = "This page is currently not visible in listings but is accessible via direct URL."
    elif page.status == PAGE_STATUS_DEACTIVATED:
        show_banner = True
        banner_message = "This page is currently deactivated."
    elif page.status == 'HIDDEN':
        # HIDDEN pages visible to admins only
        if not request.user.is_authenticated or (not _is_super_admin(request.user) and not _is_admin_pandit(request.user)):
            raise Http404("Page not found")
    
    # Check permissions using permission service
    can_edit = False
    can_edit_media = False
    can_manage_moderators = False
    can_create_post_permission = False
    user_page_role = None
    is_super_admin_user = _is_super_admin(request.user)
    is_admin_pandit_user = _is_admin_pandit(request.user)
    
    if request.user.is_authenticated:
        can_edit = is_page_owner(request.user, page) or is_super_admin_user
        can_edit_media = can_edit_page_media(request.user, page)
        can_upload_gallery_permission = can_upload_gallery(request.user, page)
        can_manage_moderators = can_assign_moderator(request.user, page)
        can_create_post_permission = can_create_post(request.user, page)
        user_page_role = get_user_page_role(request.user, page)
    
    # Record page view engagement
    if request.user.is_authenticated:
        try:
            record_view(
                user=request.user,
                entity_type=ENTITY_TEMPLE_PAGE,
                entity_public_id=page.public_id
            )
        except Exception:
            pass  # Don't fail if logging fails
    
    # Get pinned posts (max 5, shown below cover image)
    pinned_posts = page.posts.filter(is_pinned=True, is_hidden=False).order_by('-pinned_at')[:5]
    
    # Get regular posts (non-pinned, not hidden)
    regular_posts = page.posts.filter(is_pinned=False, is_hidden=False).order_by('-created_at')
    
    # Get reviews for this page (if page_type is TEMPLE)
    reviews = None
    star_breakdown = None
    user_helpful_votes = set()
    
    if page.page_type == 'TEMPLE':
        from .models import PageReview
        from .views_page_review_advanced import get_page_star_breakdown
        
        # Get visible reviews (not hidden)
        reviews = PageReview.objects.filter(
            page=page,
            visibility_state='visible',
            is_hidden=False
        ).order_by('-created_at')
        
        # Get star breakdown
        star_breakdown = get_page_star_breakdown(page.id)
        
        # Check which reviews user has voted helpful
        if request.user.is_authenticated:
            from .models_page_review_advanced import PageReviewHelpfulVote
            user_helpful_votes = set(
                PageReviewHelpfulVote.objects.filter(
                    user=request.user,
                    review_id__in=[r.id for r in reviews]
                ).values_list('review_id', flat=True)
            )
    
    # Get visible gallery images (not hidden)
    gallery_images = page.gallery_images.filter(is_hidden=False).order_by('-created_at')
    
    # Follow state for temple: follower_count visible to all; is_following only when authenticated
    is_following = False
    follower_count = 0
    try:
        from core.follow_service import is_following as check_is_following, get_follower_count as get_follow_count
        follower_count = get_follow_count('temple', page.id)
        if request.user.is_authenticated:
            is_following = check_is_following(request.user, 'temple', page.id)
    except Exception:
        pass
    
    # Generate JSON-LD schema (identity-only, NOT editable)
    try:
        page_schema = build_page_schema(page, request)
        page_schema_json = json.dumps(page_schema, ensure_ascii=False, indent=2)
    except Exception:
        page_schema_json = None  # Fail silently if schema generation fails
    
    context = {
        'page': page,
        'page_public_id': page.public_id,
        'show_banner': show_banner,
        'banner_message': banner_message,
        'can_edit': can_edit,
        'can_edit_media': can_edit_media,
        'can_upload_gallery': can_upload_gallery_permission,
        'can_manage_moderators': can_manage_moderators,
        'can_create_post': can_create_post_permission,
        'user_page_role': user_page_role,
        'is_super_admin': is_super_admin_user,
        'is_admin_pandit': is_admin_pandit_user,
        'user': request.user if request.user.is_authenticated else None,
        'pinned_posts': pinned_posts,
        'regular_posts': regular_posts,
        'gallery_images': gallery_images,
        'reviews': reviews,
        'star_breakdown': star_breakdown,
        'user_helpful_votes': user_helpful_votes,
        'page_schema_json': page_schema_json,  # JSON-LD schema for rich results
        'is_following': is_following,
        'follower_count': follower_count,
    }
    return render(request, 'pages/page_detail.html', context)


@login_required
def page_edit(request, page_public_id):
    """
    Edit an existing page.
    
    Rules:
    - Only page owner (Admin Pandit) or Super Admin can edit
    """
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    # Check permissions using permission service
    can_edit = is_page_owner(request.user, page) or is_super_admin(request.user)
    can_edit_media = can_edit_page_media(request.user, page)
    can_edit_slug_field = can_edit_page_slug(request.user, page)
    
    if not can_edit:
        messages.error(request, "You do not have permission to edit this page.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    from .forms import PageCreateForm
    from masterdata.models import City
    
    if request.method == 'POST':
        form = PageCreateForm(request.POST, request.FILES, instance=page, allowed_page_types=[page.page_type])
        if form.is_valid():
            try:
                # Update page fields
                page.title = form.cleaned_data['title']
                
                # Slug is immutable after creation; model.save() will restore original. Do not set from form.
                
                page.description = form.cleaned_data.get('description', '')
                page.address = form.cleaned_data.get('address', '')
                page.city = form.cleaned_data.get('city')
                page.area = form.cleaned_data.get('area')
                
                # Handle SEO fields
                seo_edited = False
                if 'seo_title' in form.cleaned_data:
                    seo_title = form.cleaned_data.get('seo_title')
                    if seo_title:
                        seo_title = seo_title.strip()
                        if seo_title:
                            if len(seo_title) > 60:
                                messages.warning(request, 'SEO title truncated to 60 characters.')
                            page.seo_title = seo_title[:60]  # Enforce max length
                            seo_edited = True
                
                if 'seo_description' in form.cleaned_data:
                    seo_description = form.cleaned_data.get('seo_description')
                    if seo_description:
                        seo_description = seo_description.strip()
                        if seo_description:
                            if len(seo_description) > 160:
                                messages.warning(request, 'SEO description truncated to 160 characters.')
                            page.seo_description = seo_description[:160]  # Enforce max length
                            seo_edited = True
                
                if 'seo_keywords' in form.cleaned_data:
                    seo_keywords = form.cleaned_data.get('seo_keywords')
                    if seo_keywords:
                        seo_keywords = seo_keywords.strip()
                        if seo_keywords:
                            page.seo_keywords = seo_keywords
                        seo_edited = True
                
                # Mark SEO as manually edited if user provided any SEO data
                if seo_edited:
                    page.seo_autogenerated = False
                else:
                    # Auto-generate SEO if not provided
                    from .seo_services import auto_generate_page_seo
                    auto_generate_page_seo(page, force=True)
                
                # Handle image uploads (only if user has permission)
                if can_edit_media:
                    if 'profile_image' in request.FILES:
                        page.profile_image = request.FILES['profile_image']
                    if 'cover_image' in request.FILES:
                        page.cover_image = request.FILES['cover_image']
                
                # Set updated_by before saving
                page.updated_by = request.user
                
                # UNIT 6: Log Super Admin action before save
                if request.user.is_superuser:
                    from dashboards.audit import log_super_admin_action
                    before_snapshot = {
                        'title': page.title,
                        'status': page.status,
                        'slug': page.slug,
                    }
                    # Get current state before save
                    try:
                        old_page = Page.objects.get(pk=page.pk)
                        before_snapshot = {
                            'title': old_page.title,
                            'status': old_page.status,
                            'slug': old_page.slug,
                        }
                    except Page.DoesNotExist:
                        pass
                
                page.full_clean()  # Validate including slug immutability
                page.save()
                
                # UNIT 6: Log Super Admin action after save
                if request.user.is_superuser:
                    after_snapshot = {
                        'title': page.title,
                        'status': page.status,
                        'slug': page.slug,
                    }
                    log_super_admin_action(
                        action_type='PAGE_EDIT',
                        target_entity=page,
                        before_snapshot=before_snapshot if 'before_snapshot' in locals() else None,
                        after_snapshot=after_snapshot,
                        actor=request.user,
                    )
                
                messages.success(request, f"Page '{page.title}' updated successfully!")
                return redirect('pages:page_detail', page_public_id=page.public_id)
            except ValidationError as e:
                logger.error(f"Validation error updating page: {str(e)}", exc_info=True)
                messages.error(request, f"Validation error: {str(e)}")
            except Exception as e:
                logger.error(f"Error updating page: {str(e)}", exc_info=True)
                messages.error(request, f"Error updating page: {str(e)}")
        else:
            # Only show error message if there are actual form errors
            if form.errors:
                messages.error(request, "Please correct the errors below.")
    else:
        form = PageCreateForm(instance=page, allowed_page_types=[page.page_type])
    
    # Get cities for dropdown
    cities = City.objects.filter(is_active=True).order_by('name')
    
    context = {
        'form': form,
        'page': page,
        'cities': cities,
        'slug_readonly': True,  # Slug cannot be modified after creation
    }
    return render(request, 'pages/page_edit.html', context)


@login_required
def page_list(request):
    """
    List pages for the current user (My Pages).
    
    Rules:
    - Admin Pandit: See pages they own
    - Pandit with Moderator role: See pages where they are moderator
    - Super Admin: See all pages
    - End Users: Cannot access
    """
    if _is_super_admin(request.user):
        pages = list_pages_for_super_admin(request.user)
        user_role_context = 'super_admin'
    elif _is_admin_pandit(request.user) or request.user.role == 'pandit':
        # Get pages where user is owner or moderator
        pages = get_pages_for_user(request.user)
        user_role_context = 'pandit'
    else:
        messages.error(request, "You do not have permission to view pages.")
        return redirect('core:home')
    
    # Add role information for each page
    pages_with_roles = []
    for page in pages:
        role = get_user_page_role(request.user, page)
        pages_with_roles.append({
            'page': page,
            'user_role': role,
        })
    
    context = {
        'pages': [item['page'] for item in pages_with_roles],
        'pages_with_roles': pages_with_roles,
        'is_admin_pandit': _is_admin_pandit(request.user),
        'is_super_admin': _is_super_admin(request.user),
    }
    return render(request, 'pages/page_list.html', context)


@login_required
def page_deactivate(request, page_public_id):
    """
    Deactivate a page (Admin Pandit only, for their own pages).
    
    Rules:
    - Admin Pandit can deactivate their own pages
    - Super Admin can deactivate any page
    """
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    # Check permissions
    can_modify = False
    if _is_super_admin(request.user):
        can_modify = True
    elif _is_admin_pandit(request.user) and page.created_by == request.user:
        can_modify = True
    
    if not can_modify:
        messages.error(request, "You do not have permission to deactivate this page.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    try:
        deactivate_page(page, request.user)
        messages.success(request, f"Page '{page.title}' deactivated successfully.")
    except Exception as e:
        logger.error(f"Error deactivating page: {str(e)}", exc_info=True)
        messages.error(request, f"Error deactivating page: {str(e)}")
    
    return redirect('pages:page_detail', page_public_id=page_public_id)


@login_required
def page_activate(request, page_public_id):
    """
    Activate a page (Admin Pandit only, for their own pages).
    
    Rules:
    - Admin Pandit can activate their own pages
    - Super Admin can activate any page
    """
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    # Check permissions
    can_modify = False
    if _is_super_admin(request.user):
        can_modify = True
    elif _is_admin_pandit(request.user) and page.created_by == request.user:
        can_modify = True
    
    if not can_modify:
        messages.error(request, "You do not have permission to activate this page.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    try:
        activate_page(page, request.user)
        messages.success(request, f"Page '{page.title}' activated successfully.")
    except Exception as e:
        logger.error(f"Error activating page: {str(e)}", exc_info=True)
        messages.error(request, f"Error activating page: {str(e)}")
    
    return redirect('pages:page_detail', page_public_id=page_public_id)


@login_required
@require_POST
@csrf_protect
def page_make_invisible(request, page_public_id):
    """
    Make a page invisible (Super Admin only).
    
    TASK SA-2: Super Admin visibility toggle
    
    Rules:
    - Only Super Admin can make pages invisible
    - INVISIBLE pages still accessible via direct URL
    - Status changes to INVISIBLE
    """
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    if not _is_super_admin(request.user):
        messages.error(request, "Only Super Admin can make pages invisible.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    try:
        make_page_invisible(request.user, page)
        messages.success(request, f"Page '{page.title}' is now invisible.")
    except Exception as e:
        logger.error(f"Error making page invisible: {str(e)}", exc_info=True)
        messages.error(request, f"Error making page invisible: {str(e)}")
    
    # Redirect back to dashboard if from dashboard, else to page detail
    if request.GET.get('from') == 'dashboard':
        return redirect('module5_dashboards:dashboard_super_admin')
    return redirect('pages:page_detail', page_public_id=page_public_id)


@login_required
@require_POST
@csrf_protect
def page_make_visible(request, page_public_id):
    """
    Make an invisible page visible (Super Admin only).
    
    TASK SA-2: Super Admin visibility toggle
    
    Rules:
    - Only Super Admin can make pages visible
    - Status changes from INVISIBLE to ACTIVE
    """
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    if not _is_super_admin(request.user):
        messages.error(request, "Only Super Admin can make pages visible.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    try:
        make_page_visible(request.user, page)
        messages.success(request, f"Page '{page.title}' is now visible.")
    except Exception as e:
        logger.error(f"Error making page visible: {str(e)}", exc_info=True)
        messages.error(request, f"Error making page visible: {str(e)}")
    
    # Redirect back to dashboard if from dashboard, else to page detail
    if request.GET.get('from') == 'dashboard':
        return redirect('module5_dashboards:dashboard_super_admin')
    return redirect('pages:page_detail', page_public_id=page_public_id)


# PART 3 HARDENING: Explicit HTTP method declaration
from django.views.decorators.http import require_http_methods

@login_required
@require_http_methods(["GET", "POST"])
def upload_gallery_image(request, page_public_id):
    """
    Upload gallery images for a page.
    
    Rules:
    - Admin Pandit can upload to their own pages
    - Super Admin can upload to any page
    """
    if reject_bigint_id(page_public_id):
        return JsonResponse({'success': False, 'error': 'Invalid page ID format'}, status=400)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({'success': False, 'error': 'Page not found'}, status=404)
    
    # PART 4: Check permissions - only moderate pandit, admin pandit, super admin can upload
    if not can_upload_gallery(request.user, page):
        return JsonResponse({'success': False, 'error': 'Permission denied. Only moderators, admin pandits, and super admins can upload gallery images.'}, status=403)
    
    if request.method == 'POST':
        images = request.FILES.getlist('images')
        caption = request.POST.get('caption', '').strip()
        
        if not images:
            return JsonResponse({'success': False, 'error': 'No images provided'}, status=400)
        
        # PART 4: Validate max 20 images
        if len(images) > 20:
            return JsonResponse({'success': False, 'error': 'Maximum 20 images allowed per upload'}, status=400)
        
        # PART 4 FIX: Centralized file upload validation
        from core.file_upload_security import validate_image_upload
        from django.core.exceptions import ValidationError
        
        validated_images = []
        for image in images:
            try:
                sanitized_filename, validated_file = validate_image_upload(image)
                validated_images.append(validated_file)
            except ValidationError as e:
                return JsonResponse({'success': False, 'error': f'Image validation failed: {str(e)}'}, status=400)
        
        uploaded_images = []
        for validated_image in validated_images:
            try:
                gallery_image = PageGalleryImage.objects.create(
                    page=page,
                    image=validated_image,
                    caption=caption,
                    uploaded_by=request.user,
                    is_hidden=False
                )
                uploaded_images.append({
                    'public_id': gallery_image.public_id,
                    'url': gallery_image.image.url,
                    'caption': gallery_image.caption
                })
            except Exception as e:
                logger.error(f"Error uploading gallery image: {str(e)}", exc_info=True)
                return JsonResponse({'success': False, 'error': f'Error uploading image: {str(e)}'}, status=500)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_images)} image(s)',
            'images': uploaded_images
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


@login_required
def delete_gallery_image(request, page_public_id, image_public_id):
    """
    Delete a gallery image (soft delete - set is_hidden=True).
    
    Rules:
    - Admin Pandit can delete only their own images
    - Super Admin cannot delete (can only hide/unhide)
    """
    if reject_bigint_id(page_public_id) or reject_bigint_id(image_public_id):
        return JsonResponse({'success': False, 'error': 'Invalid ID format'}, status=400)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({'success': False, 'error': 'Page not found'}, status=404)
    
    gallery_image = resolve_public_id(PageGalleryImage, image_public_id)
    if not gallery_image or gallery_image.page != page:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)
    
    # TASK 6: Check permissions - moderators can delete only their own images
    # Super Admin cannot delete (only hide/unhide)
    if _is_super_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Super Admin cannot delete images. Use hide/unhide instead.'}, status=403)
    
    # Check if user can edit page media (owner or moderator)
    if not can_edit_page_media(request.user, page):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # Moderators can only delete their own images
    from .page_permissions import is_page_moderator
    if is_page_moderator(request.user, page) and gallery_image.uploaded_by != request.user:
        return JsonResponse({'success': False, 'error': 'You can only delete images you uploaded'}, status=403)
    
    # Soft delete: set is_hidden=True (no hard deletes)
    gallery_image.is_hidden = True
    gallery_image.save(update_fields=['is_hidden'])
    return JsonResponse({
        'success': True,
        'message': 'Image deleted successfully'
    })


@login_required
def toggle_gallery_image_visibility(request, page_public_id, image_public_id):
    """
    Hide/unhide a gallery image (Super Admin only).
    
    Security:
    - Only Super Admin can hide/unhide
    - Uses public_id to prevent enumeration
    """
    from django.http import JsonResponse
    
    if reject_bigint_id(page_public_id) or reject_bigint_id(image_public_id):
        return JsonResponse({'success': False, 'error': 'Invalid ID format'}, status=400)
    
    if not _is_super_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Only Super Admin can hide/unhide images'}, status=403)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({'success': False, 'error': 'Page not found'}, status=404)
    
    gallery_image = resolve_public_id(PageGalleryImage, image_public_id)
    if not gallery_image or gallery_image.page != page:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)
    
    if request.method == 'POST':
        gallery_image.is_hidden = not gallery_image.is_hidden
        gallery_image.save(update_fields=['is_hidden'])
        return JsonResponse({
            'success': True,
            'is_hidden': gallery_image.is_hidden,
            'message': 'Image hidden' if gallery_image.is_hidden else 'Image visible'
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)


@login_required
@require_POST
@csrf_protect
def submit_review(request, page_public_id):
    """
    Submit a review for a temple page.
    
    Rules:
    - End users can submit reviews
    - Admin Pandit cannot review their own pages
    - One review per user per page
    """
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    # Check if user already reviewed this page
    existing_review = PageReview.objects.filter(page=page, user=request.user).first()
    if existing_review:
        messages.error(request, "You have already submitted a review for this page.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    # Check if user is trying to review their own page
    if page.created_by == request.user:
        messages.error(request, "You cannot review your own page.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    rating = request.POST.get('rating')
    review_text = request.POST.get('review_text', '').strip()
    
    if not rating or not review_text:
        messages.error(request, "Rating and review text are required.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
    except (ValueError, TypeError):
        messages.error(request, "Invalid rating. Please select a rating between 1 and 5.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    try:
        review = PageReview.objects.create(
            page=page,
            user=request.user,
            rating=rating,
            review_text=review_text,
            visibility_state=PageReview.VISIBLE
        )
        
        # Log engagement event
        try:
            from engagement.models import UserInteractionEvent
            from engagement.constants import ENTITY_TEMPLE_PAGE, INTERACTION_COMMENT_CREATE
            
            UserInteractionEvent.objects.create(
                user=request.user,
                entity_type=ENTITY_TEMPLE_PAGE,
                entity_public_id=page.public_id,
                interaction_type=INTERACTION_COMMENT_CREATE,  # Review is similar to comment
                metadata={'review_public_id': review.public_id}
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        messages.success(request, "Thank you for your review!")
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error submitting review: {str(e)}")
    
    return redirect('pages:page_detail', page_public_id=page_public_id)


@login_required
def search_pandits(request, page_public_id):
    """
    Search Pandits by email for moderator assignment (Owner only).
    
    TASK 1: Pandit search by email
    """
    if reject_bigint_id(page_public_id):
        return JsonResponse({'success': False, 'error': 'Invalid page ID format'}, status=400)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({'success': False, 'error': 'Page not found'}, status=404)
    
    # Check permissions - only Page OWNER can search
    if not can_assign_moderator(request.user, page):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    email_query = request.GET.get('email', '').strip()
    if not email_query:
        return JsonResponse({'success': False, 'error': 'email parameter is required'}, status=400)
    
    # Search pandits by email (case-insensitive, partial match)
    from accounts.models import User
    from pages.models import PageRole
    
    # Get existing moderators to exclude
    existing_moderator_ids = PageRole.objects.filter(
        page=page
    ).values_list('pandit_id', flat=True)
    
    # Search only Pandits, exclude owner, exclude existing moderators
    pandits = User.objects.filter(
        role='pandit',
        status='active',
        is_active=True,
        email__icontains=email_query
    ).exclude(
        id=page.created_by.id
    ).exclude(
        id__in=existing_moderator_ids
    )[:10]  # Limit to 10 results
    
    # Get current roles for each pandit (if any on this page)
    results = []
    for pandit in pandits:
        current_role = PageRole.objects.filter(
            page=page,
            pandit=pandit
        ).first()
        
        # Get city if available
        city_name = None
        try:
            if hasattr(pandit, 'pandit_profile') and pandit.pandit_profile:
                if hasattr(pandit.pandit_profile, 'city') and pandit.pandit_profile.city:
                    city_name = pandit.pandit_profile.city.name
        except Exception:
            pass
        
        results.append({
            'id': pandit.id,
            'public_id': str(pandit.public_id) if hasattr(pandit, 'public_id') else None,
            'email': pandit.email,
            'name': pandit.get_full_name() or pandit.email,
            'city': city_name,
            'current_role': current_role.get_role_display() if current_role else None,
        })
    
    # Log search attempt (audit only)
    try:
        from .models import PageAuditLog
        from .constants import AUDIT_ACTION_UPDATE
        PageAuditLog.objects.create(
            page=page,
            action=AUDIT_ACTION_UPDATE,
            performed_by=request.user
        )
    except Exception:
        pass  # Don't fail if audit logging fails
    
    return JsonResponse({
        'success': True,
        'results': results,
        'count': len(results)
    })


@login_required
def manage_moderators(request, page_public_id):
    """
    Manage moderators for a page (Owner only).
    
    Rules:
    - Only page owner can assign/remove moderators
    - Only Pandits can be assigned as moderators
    - Super Admin can also manage moderators
    """
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    # Check permissions
    if not can_assign_moderator(request.user, page):
        messages.error(request, "You do not have permission to manage moderators for this page.")
        return redirect('pages:page_detail', page_public_id=page_public_id)
    
    # Get current moderators
    moderators = PageRole.objects.filter(
        page=page,
        role=PageRole.ROLE_MODERATOR
    ).select_related('pandit')
    
    context = {
        'page': page,
        'moderators': moderators,
        'can_assign': can_assign_moderator(request.user, page),
    }
    
    return render(request, 'pages/manage_moderators.html', context)


@login_required
@require_POST
@csrf_protect
def assign_moderator(request, page_public_id):
    """
    Assign a moderator role to a pandit (Owner only).
    
    POST params:
    - pandit_id: ID of the pandit to assign
    """
    if reject_bigint_id(page_public_id):
        return JsonResponse({'success': False, 'error': 'Invalid page ID format'}, status=400)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({'success': False, 'error': 'Page not found'}, status=404)
    
    # Check permissions
    if not can_assign_moderator(request.user, page):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # TASK 2: Support both pandit_id and pandit_public_id
    pandit_id = request.POST.get('pandit_id')
    pandit_public_id = request.POST.get('pandit_public_id')
    
    if not pandit_id and not pandit_public_id:
        return JsonResponse({'success': False, 'error': 'pandit_id or pandit_public_id is required'}, status=400)
    
    # Get pandit
    from accounts.models import User
    from core.public_id import resolve_public_id
    
    try:
        if pandit_public_id:
            # Resolve by public_id
            pandit = resolve_public_id(User, pandit_public_id)
            if not pandit:
                return JsonResponse({'success': False, 'error': 'Pandit not found'}, status=404)
        else:
            # Resolve by ID
            try:
                pandit_id = int(pandit_id)
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': 'Invalid pandit_id'}, status=400)
            pandit = User.objects.get(id=pandit_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Pandit not found'}, status=404)
    
    # TASK 2: Validate pandit role and status
    if pandit.role != 'pandit':
        return JsonResponse({'success': False, 'error': 'User must be a Pandit to be assigned as moderator'}, status=400)
    
    if not pandit.is_active or pandit.status != 'active':
        return JsonResponse({'success': False, 'error': 'Pandit must be active to be assigned as moderator'}, status=400)
    
    # TASK 2: Cannot assign Admin Pandit or End User
    if pandit.role == 'admin' or pandit.is_superuser:
        return JsonResponse({'success': False, 'error': 'Admin Pandits cannot be assigned as moderators'}, status=400)
    
    # Check if already has a role
    existing_role = PageRole.objects.filter(page=page, pandit=pandit).first()
    if existing_role:
        return JsonResponse({'success': False, 'error': f'Pandit already has role: {existing_role.get_role_display()}'}, status=400)

    from django.db import IntegrityError, OperationalError

    try:
        PageRole.objects.create(
            page=page,
            pandit=pandit,
            role=PageRole.ROLE_MODERATOR
        )
    except IntegrityError as e:
        logger.warning(f"Assign moderator IntegrityError: {e}")
        return JsonResponse({
            'success': False,
            'error': 'This pandit may already be assigned to this page. Refresh the list and try again.',
        }, status=400)
    except OperationalError as e:
        logger.error(f"Assign moderator OperationalError (table/schema?): {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Database error. Ensure migrations are run (e.g. python manage.py migrate).',
        }, status=500)
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error assigning moderator: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    try:
        from .models import PageAuditLog
        from .constants import AUDIT_ACTION_UPDATE
        PageAuditLog.objects.create(
            page=page,
            action=AUDIT_ACTION_UPDATE,
            performed_by=request.user
        )
    except Exception as e:
        logger.warning(f"Audit log failed for moderator assign: {e}")

    try:
        from notifications.services import NotificationService
        from notifications.constants import NOTIFICATION_TYPE_PAGE_MODERATOR_ASSIGNED
        NotificationService.create_notification(
            recipient=pandit,
            notification_type=NOTIFICATION_TYPE_PAGE_MODERATOR_ASSIGNED,
            source_module='pages',
            payload={
                'page_public_id': getattr(page, 'public_id', None) or '',
                'page_title': page.title,
                'role_assigned': 'MODERATOR',
            }
        )
    except Exception as e:
        logger.warning(f"Failed to create notification for moderator assignment: {str(e)}")

    return JsonResponse({'success': True, 'message': f'Moderator {pandit.email} assigned successfully'})


@login_required
@require_POST
@csrf_protect
def remove_moderator(request, page_public_id):
    """
    Remove a moderator role from a pandit (Owner only).
    
    POST params:
    - pandit_id: ID of the pandit to remove
    """
    if reject_bigint_id(page_public_id):
        return JsonResponse({'success': False, 'error': 'Invalid page ID format'}, status=400)
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        return JsonResponse({'success': False, 'error': 'Page not found'}, status=404)
    
    # Check permissions
    if not can_assign_moderator(request.user, page):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    pandit_id = request.POST.get('pandit_id')
    if not pandit_id:
        return JsonResponse({'success': False, 'error': 'pandit_id is required'}, status=400)
    
    try:
        pandit_id = int(pandit_id)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid pandit_id'}, status=400)
    
    # Get and remove moderator role
    try:
        role = PageRole.objects.get(page=page, pandit_id=pandit_id, role=PageRole.ROLE_MODERATOR)
        pandit_email = role.pandit.email
        role.delete()
        
        # Log audit
        from .models import PageAuditLog
        from .constants import AUDIT_ACTION_UPDATE
        PageAuditLog.objects.create(
            page=page,
            action=AUDIT_ACTION_UPDATE,
            performed_by=request.user
        )
        
        return JsonResponse({'success': True, 'message': f'Moderator {pandit_email} removed successfully'})
    except PageRole.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Moderator role not found'}, status=404)
    except Exception as e:
        logger.error(f"Error removing moderator: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Error removing moderator: {str(e)}'}, status=500)
