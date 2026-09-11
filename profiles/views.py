"""
Profiles views for Pandit profile display and management.

Security Rules:
- Public profiles: Only visible if profile is approved and user is active
- Private profiles: Only accessible by profile owner
- Edit profiles: Only accessible by profile owner
- All views use public_id (UUIDv7) to prevent enumeration attacks
"""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404, HttpResponseForbidden
from .models import PanditProfile
from core.public_id import resolve_public_id, reject_bigint_id
from seo.schema_builders import build_pandit_schema


def _pandit_profile_phone_verification_context(request, profile):
    """Sync profile phone to User.phone_number and expose OTP verification UI context."""

    from otp_verification import constants as otp_constants
    from otp_verification.registration.completions import _sync_expert_user_phone
    from otp_verification.registration.factory import is_registration_otp_required

    profile_phone = (
        (profile.call_mobile_number or "")
        or (profile.primary_mobile_number or "")
        or (profile.phone_number or "")
    ).strip()
    user = request.user
    if profile_phone and hasattr(user, "phone_number"):
        if user.phone_number != profile_phone:
            _sync_expert_user_phone(user, profile_phone)

    return {
        "phone_is_verified": bool(getattr(user, "is_phone_verified", False)),
        "pandit_otp_required": is_registration_otp_required(
            otp_constants.FLOW_PANDIT_REGISTRATION
        ),
    }


def profile_public(request, identifier=None, public_id=None):
    """
    Public view of a Pandit profile.
    
    Phase 11B.1: Accepts both identifier (slug or legacy) and public_id (explicit route).
    - URL name profile_public: path <identifier>/ (slug or public_id as segment)
    - URL name profile_public_by_id: path id/<public_id>/
    
    Security:
    - Uses public_id (UUIDv7) or slug to prevent enumeration
    - Rejects BIGINT IDs for security
    - Only shows approved profiles
    - Only shows profiles for active users
    - Prevents access to unapproved or inactive profiles
    
    Accessible to all users (logged-in and anonymous) for approved profiles only.
    """
    profile = None

    if public_id:
        # Explicit public_id route (profile_public_by_id)
        if reject_bigint_id(public_id):
            raise Http404("Invalid profile identifier")
        profile = resolve_public_id(PanditProfile, public_id)
        if not profile:
            raise Http404("Profile not found")
    else:
        # identifier route (profile_public): slug or public_id as path segment
        try:
            profile = PanditProfile.objects.get(slug=identifier, is_profile_approved=True)
        except PanditProfile.DoesNotExist:
            pass

        if not profile:
            if reject_bigint_id(identifier):
                raise Http404("Invalid profile identifier")
            profile = resolve_public_id(PanditProfile, identifier)
            if not profile:
                raise Http404("Profile not found")
    
    # Check if user is the profile owner
    is_profile_owner = request.user.is_authenticated and request.user == profile.user
    
    # Security: Only show approved profiles for active users
    # Exception: Profile owners can view their own profile even if not approved
    is_approved = profile.is_profile_approved
    is_active_user = (profile.user.status == 'active' and 
                     profile.user.is_active and 
                     profile.user.role == 'pandit')
    
    if not is_active_user:
        # Don't reveal if user is inactive
        raise Http404("Profile not found")
    
    # If profile is not approved, only show to owner
    if not is_approved and not is_profile_owner:
        # Don't reveal if profile exists but is not approved (unless owner)
        raise Http404("Profile not found")
    
    # Additional security: Check if profile owner wants to hide profile
    # (This would be handled by governance module in production)
    
    # Generate JSON-LD schema (identity-only, NOT editable)
    try:
        pandit_schema = build_pandit_schema(profile, request)
        pandit_schema_json = json.dumps(pandit_schema, ensure_ascii=False, indent=2)
    except Exception:
        pandit_schema_json = None  # Fail silently if schema generation fails
    
    # Get reviews for this pandit (first 5 for inline display)
    from reviews.models import Review
    from reviews.services import ReviewService
    from reviews.permissions import can_create_review
    
    pandit_reviews = ReviewService.get_visible_reviews_for_pandit(profile.user.id)[:5]
    rating_aggregation = ReviewService.get_rating_aggregation_for_pandit(profile.user.id)
    
    # Check if current user can submit review
    # User can only submit ONE review per pandit (regardless of visibility state)
    can_submit_review = False
    if request.user.is_authenticated:
        # Check if user has permission to create reviews AND hasn't already reviewed this pandit
        can_submit_review = can_create_review(request.user) and not Review.objects.filter(
            user=request.user,
            pandit=profile.user
            # Note: We check for ANY review, not just visible ones, to enforce one-review-per-user rule
        ).exists()
    
    # Follower count for pandit (visible on public profile for everyone)
    follower_count = 0
    try:
        from core.follow_service import get_follower_count as get_follow_count
        follower_count = get_follow_count('pandit', profile.id)
    except Exception:
        pass

    # Phase 14: Behavior analytics (passive; profile view engagement)
    try:
        from behavior_engine.trackers import track_pandit_view
        track_pandit_view(request, profile.id, metadata={})
    except Exception:
        pass

    # Prepare context for template
    context = {
        'pandit': profile,
        'user': request.user if request.user.is_authenticated else None,
        'is_profile_owner': is_profile_owner,
        'profile_public_id': profile.public_id,  # Use public_id in templates
        'is_profile_approved': is_approved,  # Pass approval status for template warnings
        'profile_state': 'pending' if not is_approved else 'active',  # For template state handling
        'pandit_schema_json': pandit_schema_json,  # JSON-LD schema for rich results
        'pandit_reviews': pandit_reviews,  # First 5 reviews for inline display
        'ratings_summary': rating_aggregation,  # Rating aggregation
        'can_submit_review': can_submit_review,  # Whether user can submit review
        'follower_count': follower_count,
    }
    
    return render(request, 'module4_profile/profile_public.html', context)


@login_required
def profile_edit(request, public_id=None):
    """
    Edit view for Pandit profile.
    
    Security:
    - Only profile owner can edit their own profile
    - Uses public_id (UUIDv7) to prevent unauthorized access
    - Validates user is the profile owner before allowing edits
    
    Allows Pandits to edit their own profile only.
    """
    # Import models needed for this view
    from masterdata.models import City, LocalArea, Pooja, Language
    
    # Safety: Ensure user has a pandit profile - auto-create if missing
    profile = None
    
    # Get or create profile
    if public_id:
        # Security: Reject BIGINT IDs
        if reject_bigint_id(public_id):
            messages.error(request, "Invalid profile identifier.")
            return redirect('profiles:profile_private')
        
        profile = resolve_public_id(PanditProfile, public_id)
        if not profile:
            messages.error(request, "Profile not found.")
            return redirect('profiles:profile_private')
        
        # Security: Ensure user can only edit their own profile
        if profile.user != request.user:
            messages.error(request, "You don't have permission to edit this profile.")
            return redirect('profiles:profile_private')
    else:
        # 🔒 SAFE: Get profile using filter().first() to avoid relationship cache issues
        # This is safer than accessing request.user.pandit_profile directly
        if request.user.role == 'pandit':
            profile = PanditProfile.objects.filter(user=request.user).first()
            
            # If no profile exists, create it
            if not profile:
                profile = PanditProfile(user=request.user)
                # Save immediately to get primary key (required before M2M access)
                profile.save()
        else:
            messages.error(request, "You don't have a Pandit profile.")
            return redirect('core:home')
    
    # 🔒 CRITICAL: Ensure profile is saved and has a primary key before accessing M2M fields
    # This prevents "needs to have a value for field 'id' before M2M can be used" error
    if profile.pk is None:
        profile.save()
    
    # Refresh profile from database to ensure it's fully loaded with all relationships
    profile.refresh_from_db()
    
    # Security: Double-check ownership
    if profile.user != request.user:
        messages.error(request, "Access denied. You can only edit your own profile.")
        return redirect('profiles:profile_private')
    
    # Security: Ensure user is a pandit
    if request.user.role != 'pandit':
        messages.error(request, "Only Pandits can edit profiles.")
        return redirect('core:home')
    
    if request.method == 'POST':
        # Handle form submission
        try:
            old_call_mobile = (profile.call_mobile_number or "").strip()

            # Update basic fields
            if 'about_description' in request.POST:
                profile.about_description = request.POST.get('about_description', '').strip()
            
            # Update languages (M2M field - preferred)
            if 'languages' in request.POST:
                language_ids = request.POST.getlist('languages')
                languages = Language.objects.filter(id__in=language_ids, is_active=True, status=Language.STATUS_ACTIVE)
                profile.languages.set(languages)
            
            # Keep languages_spoken for backward compatibility (legacy field)
            if 'languages_spoken' in request.POST:
                profile.languages_spoken = request.POST.get('languages_spoken', '').strip()
            
            # Update phone number and contact preferences (legacy support)
            if 'phone_number' in request.POST:
                phone_number = request.POST.get('phone_number', '').strip()
                profile.phone_number = phone_number if phone_number else None
            
            # Update primary mobile number (legacy - kept for backward compatibility)
            if 'primary_mobile_number' in request.POST:
                primary_mobile = request.POST.get('primary_mobile_number', '').strip()
                profile.primary_mobile_number = primary_mobile if primary_mobile else None
            
            # Update secondary mobile number
            if 'secondary_mobile_number' in request.POST:
                secondary_mobile = request.POST.get('secondary_mobile_number', '').strip()
                profile.secondary_mobile_number = secondary_mobile if secondary_mobile else None
            
            # NEW: Update call mobile number
            if 'call_mobile_number' in request.POST:
                call_mobile = request.POST.get('call_mobile_number', '').strip()
                # Validate: Only digits and optional + prefix
                if call_mobile:
                    # Remove any spaces or dashes
                    call_mobile = call_mobile.replace(' ', '').replace('-', '')
                    # Validate format (digits only, optional + prefix)
                    if call_mobile.startswith('+'):
                        if not call_mobile[1:].isdigit() or len(call_mobile) < 11 or len(call_mobile) > 15:
                            messages.error(request, 'Invalid calling mobile number format. Use digits only with optional + prefix (e.g., +919876543210).')
                            return redirect('profiles:profile_edit')
                    elif not call_mobile.isdigit() or len(call_mobile) < 10 or len(call_mobile) > 15:
                        messages.error(request, 'Invalid calling mobile number format. Use digits only with optional + prefix (e.g., +919876543210).')
                        return redirect('profiles:profile_edit')
                    # One phone number = one User account (exclude self).
                    from accounts.phone_utils import normalize_phone_number, phone_already_registered

                    normalized_call = normalize_phone_number(call_mobile)
                    if not normalized_call:
                        messages.error(request, 'Phone number format is invalid.')
                        return redirect('profiles:profile_edit')
                    if phone_already_registered(
                        normalized_call, exclude_user_id=request.user.pk
                    ):
                        messages.error(request, 'Phone number already registered')
                        return redirect('profiles:profile_edit')
                profile.call_mobile_number = call_mobile if call_mobile else None
            else:
                # If not provided, clear it
                profile.call_mobile_number = None
            
            # NEW: Update WhatsApp mobile number (works on Railway, GoDaddy, VPS: hidden input sends "0" when unchecked)
            use_same_val = request.POST.get('use_same_number_for_call_and_whatsapp', '0').strip().lower()
            use_same_number = use_same_val in ('1', 'on', 'true', 'yes')
            profile.use_same_number_for_call_and_whatsapp = use_same_number
            
            if use_same_number:
                # If checkbox is checked, WhatsApp number mirrors calling number
                profile.whatsapp_mobile_number = profile.call_mobile_number
            else:
                # If checkbox is unchecked, allow separate WhatsApp number
                if 'whatsapp_mobile_number' in request.POST:
                    whatsapp_mobile = request.POST.get('whatsapp_mobile_number', '').strip()
                    # Validate: Only digits and optional + prefix
                    if whatsapp_mobile:
                        # Remove any spaces or dashes
                        whatsapp_mobile = whatsapp_mobile.replace(' ', '').replace('-', '')
                        # Validate format (digits only, optional + prefix)
                        if whatsapp_mobile.startswith('+'):
                            if not whatsapp_mobile[1:].isdigit() or len(whatsapp_mobile) < 11 or len(whatsapp_mobile) > 15:
                                messages.error(request, 'Invalid WhatsApp mobile number format. Use digits only with optional + prefix (e.g., +919876543210).')
                                return redirect('profiles:profile_edit')
                        elif not whatsapp_mobile.isdigit() or len(whatsapp_mobile) < 10 or len(whatsapp_mobile) > 15:
                            messages.error(request, 'Invalid WhatsApp mobile number format. Use digits only with optional + prefix (e.g., +919876543210).')
                            return redirect('profiles:profile_edit')
                    profile.whatsapp_mobile_number = whatsapp_mobile if whatsapp_mobile else None
                else:
                    profile.whatsapp_mobile_number = None
            
            # Validation: At least one mobile number must exist (call or legacy primary)
            if not profile.call_mobile_number and not profile.primary_mobile_number:
                messages.error(request, 'At least one mobile number (Calling) is required.')
                return redirect('profiles:profile_edit')
            
            # Auto-enable call/whatsapp if phone numbers are provided
            # If call_mobile_number exists, enable call by default
            if profile.call_mobile_number:
                profile.enable_call = True
                profile.allow_call = True
            
            # If whatsapp_mobile_number exists or use_same_number is checked, enable WhatsApp (so WhatsApp button shows)
            if profile.whatsapp_mobile_number or (getattr(profile, 'use_same_number_for_call_and_whatsapp', False) and profile.call_mobile_number):
                profile.enable_whatsapp = True
                profile.allow_whatsapp = True
            
            # Update enable_call checkbox if explicitly provided in form (allows disabling)
            if 'enable_call' in request.POST:
                profile.enable_call = 'enable_call' in request.POST
                profile.allow_call = profile.enable_call
            
            # Update enable_whatsapp checkbox if explicitly provided in form (allows disabling)
            if 'enable_whatsapp' in request.POST:
                profile.enable_whatsapp = 'enable_whatsapp' in request.POST
                profile.allow_whatsapp = profile.enable_whatsapp
            
            # Update experience_years if provided
            # Note: Template might use 'experience' field name, but model uses 'experience_years'
            if 'experience_years' in request.POST:
                try:
                    exp_years = request.POST.get('experience_years', '').strip()
                    if exp_years:
                        profile.experience_years = int(exp_years)
                except (ValueError, TypeError):
                    pass
            elif 'experience' in request.POST:
                # Handle if template uses 'experience' field name
                try:
                    exp_years = request.POST.get('experience', '').strip()
                    if exp_years:
                        profile.experience_years = int(exp_years)
                except (ValueError, TypeError):
                    pass
            
            # Update ManyToMany relationships
            if 'poojas' in request.POST:
                pooja_ids = request.POST.getlist('poojas')
                from masterdata.models import Pooja
                poojas = Pooja.objects.filter(id__in=pooja_ids, is_active=True)
                profile.poojas_performed.set(poojas)
            
            if 'city' in request.POST:
                import re
                from masterdata.models import City
                city_id = request.POST.get('city', '').strip()
                if city_id == 'others':
                    MAX_CUSTOM_LEN = 100

                    # Require state when adding a new city (State → City → Area hierarchy)
                    raw_state_choice = request.POST.get('state', '').strip()
                    if raw_state_choice == 'others':
                        raw_custom_state = request.POST.get('new_state_name', '').strip()
                        if not raw_custom_state:
                            messages.error(request, 'Please enter your state name when selecting "Others".')
                            return redirect('profiles:profile_edit')
                        raw_state_value = raw_custom_state
                    else:
                        raw_state_value = raw_state_choice

                    state_value = re.sub(r'\s+', ' ', raw_state_value).strip().title() if raw_state_value else ''
                    if not state_value:
                        messages.error(request, 'Please select or enter a state when adding a new city (State → City → Area).')
                        return redirect('profiles:profile_edit')

                    if len(state_value) > MAX_CUSTOM_LEN:
                        messages.error(request, f'State name must be at most {MAX_CUSTOM_LEN} characters.')
                        return redirect('profiles:profile_edit')

                    new_city_name = request.POST.get('new_city_name', '').strip()
                    new_city_name = re.sub(r'\s+', ' ', new_city_name).strip()
                    if not new_city_name:
                        messages.error(request, 'Please enter your city name when selecting "Others".')
                        return redirect('profiles:profile_edit')
                    if len(new_city_name) < 2:
                        messages.error(request, 'City name must be at least 2 characters long.')
                        return redirect('profiles:profile_edit')

                    if len(new_city_name) > MAX_CUSTOM_LEN:
                        messages.error(request, f'City name must be at most {MAX_CUSTOM_LEN} characters.')
                        return redirect('profiles:profile_edit')

                    if not re.match(r'^[a-zA-Z\s\-\.\']+$', new_city_name):
                        messages.error(request, 'City name can only contain letters, spaces, hyphens, and periods.')
                        return redirect('profiles:profile_edit')
                    new_city_name = new_city_name.title()

                    if len(new_city_name) > MAX_CUSTOM_LEN:
                        messages.error(request, f'City name must be at most {MAX_CUSTOM_LEN} characters.')
                        return redirect('profiles:profile_edit')

                    # SAFE: store "Others" selections on the profile only.
                    # No masterdata writes (no City/LocalArea creation) to preserve master data integrity.
                    profile.custom_state_name = state_value
                    profile.custom_city_name = new_city_name
                    profile.custom_area_name = None
                    profile.cities_served.clear()
                    profile.areas_served.clear()
                    messages.success(
                        request,
                        f'City "{new_city_name}" saved safely. It will not appear in search filters until admin approval.'
                    )
                elif city_id and city_id.isdigit():
                    try:
                        city = City.objects.get(id=city_id, is_active=True)
                        # Clear custom location inputs when master city is selected.
                        profile.custom_state_name = None
                        profile.custom_city_name = None
                        profile.custom_area_name = None
                        profile.cities_served.set([city])
                    except City.DoesNotExist:
                        pass
                else:
                    # Clear master and custom location inputs.
                    profile.cities_served.clear()
                    profile.custom_state_name = None
                    profile.custom_city_name = None
                    profile.custom_area_name = None
            
            if 'area' in request.POST:
                area_id = request.POST.get('area')
                if area_id == 'other':
                    MAX_CUSTOM_LEN = 100

                    # Handle custom area creation
                    custom_area_name = request.POST.get('custom_local_area', '').strip()
                    if custom_area_name:
                        import re
                        from django.utils.text import slugify
                        from masterdata.models import LocalArea, City
                        from django.core.exceptions import ValidationError
                        # messages is already imported at module level
                        
                        # Normalize the area name
                        custom_area_name = re.sub(r'\s+', ' ', custom_area_name)  # Remove extra spaces
                        custom_area_name = custom_area_name.strip()
                        custom_area_name = custom_area_name.title()  # Capitalize properly

                        # Length safety
                        if len(custom_area_name) > MAX_CUSTOM_LEN:
                            messages.error(request, f'Local area name must be at most {MAX_CUSTOM_LEN} characters.')
                            return redirect('profiles:profile_edit')
                        
                        # Validate
                        if len(custom_area_name) < 3:
                            messages.error(request, 'Local area name must be at least 3 characters long.')
                            return redirect('profiles:profile_edit')
                        
                        # Only allow letters, spaces, and hyphens
                        if not re.match(r'^[a-zA-Z\s\-]+$', custom_area_name):
                            messages.error(request, 'Local area name can only contain letters, spaces, and hyphens.')
                            return redirect('profiles:profile_edit')
                        
                        # Get the selected city (required for area creation). When city was "others", we already set cities_served above.
                        selected_city = None
                        city_id = request.POST.get('city', '')
                        if city_id and city_id != 'others' and city_id.isdigit():
                            try:
                                # Allow linking to the selected city even if it's pending/inactive.
                                # Prefer the city already selected in this profile (safe).
                                selected_city = profile.cities_served.filter(id=city_id).first()
                            except City.DoesNotExist:
                                pass
                        if not selected_city:
                            selected_city = profile.cities_served.first()
                        
                        if not selected_city:
                            # If city came from "Others", we store it safely on profile (no master writes).
                            if not (profile.custom_city_name or '').strip():
                                messages.error(request, 'Please select a city first before adding a custom area.')
                                return redirect('profiles:profile_edit')
                            # Continue: custom_city_name exists on profile.
                        
                        # SAFE: store "Others" area on profile only (no LocalArea creation).
                        profile.custom_area_name = custom_area_name
                        profile.areas_served.clear()
                        messages.success(
                            request,
                            f'Area "{custom_area_name}" saved safely. It will not appear in search filters until admin approval.'
                        )
                    else:
                        messages.error(request, 'Please enter a local area name.')
                        return redirect('profiles:profile_edit')
                elif area_id:
                    from masterdata.models import LocalArea
                    try:
                        # Allow linking even if the area is pending/inactive (since it may be user-submitted).
                        area = LocalArea.objects.get(id=area_id)
                        # Clear custom area when master area is selected.
                        profile.custom_area_name = None
                        profile.areas_served.set([area])
                    except LocalArea.DoesNotExist:
                        pass
                else:
                    profile.custom_area_name = None
                    profile.areas_served.clear()
            
            # Handle cover image upload (if field exists)
            if 'cover_image' in request.FILES:
                # Only update if field exists on model
                if hasattr(profile, 'cover_image'):
                    # PART 4 FIX: Centralized file upload validation
                    try:
                        from core.file_upload_security import validate_image_upload
                        from django.core.exceptions import ValidationError
                        sanitized_filename, validated_file = validate_image_upload(request.FILES['cover_image'])
                        profile.cover_image = validated_file
                    except ValidationError as e:
                        messages.error(request, f'Cover image validation failed: {str(e)}')
                        return redirect('profiles:profile_edit')
            
            # Handle profile image upload (if field exists)
            if 'profile_image' in request.FILES:
                # Only update if field exists on model
                if hasattr(profile, 'profile_image'):
                    # PART 4 FIX: Centralized file upload validation
                    try:
                        from core.file_upload_security import validate_image_upload
                        from django.core.exceptions import ValidationError
                        sanitized_filename, validated_file = validate_image_upload(request.FILES['profile_image'])
                        profile.profile_image = validated_file
                    except ValidationError as e:
                        messages.error(request, f'Profile image validation failed: {str(e)}')
                        return redirect('profiles:profile_edit')
            
            # Handle SEO fields
            seo_edited = False
            if 'seo_title' in request.POST:
                seo_title = request.POST.get('seo_title', '').strip()
                if seo_title:
                    if len(seo_title) > 60:
                        messages.warning(request, 'SEO title truncated to 60 characters.')
                        seo_title = seo_title[:60]
                    profile.seo_title = seo_title
                    seo_edited = True
            
            if 'seo_description' in request.POST:
                seo_description = request.POST.get('seo_description', '').strip()
                if seo_description:
                    if len(seo_description) > 160:
                        messages.warning(request, 'SEO description truncated to 160 characters.')
                        seo_description = seo_description[:160]
                    profile.seo_description = seo_description
                    seo_edited = True
            
            if 'seo_keywords' in request.POST:
                seo_keywords = request.POST.get('seo_keywords', '').strip()
                profile.seo_keywords = seo_keywords
                seo_edited = True
            
            # Mark SEO as manually edited if user provided any SEO data
            if seo_edited:
                profile.seo_autogenerated = False
            else:
                # Auto-generate SEO if not provided
                from .seo_services import auto_generate_pandit_seo
                auto_generate_pandit_seo(profile, force=True)
            
            # Set updated_by before saving
            profile.updated_by = request.user
            
            # Save the profile
            profile.save()

            from otp_verification.registration.completions import _sync_expert_user_phone

            call_phone = (profile.call_mobile_number or "").strip()
            if call_phone:
                _sync_expert_user_phone(request.user, call_phone)
            if (
                call_phone != old_call_mobile
                and getattr(request.user, "is_phone_verified", False)
            ):
                request.user.is_phone_verified = False
                request.user.save(update_fields=["is_phone_verified", "updated_at"])

            # Enqueue admin-review entries for user-submitted "Others" locations.
            # Additive governance feature: does not modify master tables directly.
            try:
                from .models import PendingLocation
                import re

                def _norm(val: str | None) -> str:
                    v = (val or "").strip()
                    v = re.sub(r"\s+", " ", v)
                    return v.lower()

                custom_state = (profile.custom_state_name or "").strip()
                custom_city = (profile.custom_city_name or "").strip()
                custom_area = (profile.custom_area_name or "").strip()

                # State pending
                if custom_state:
                    state_norm = _norm(custom_state)
                    if not PendingLocation.objects.filter(type=PendingLocation.TYPE_STATE, normalized_name=state_norm).exists():
                        PendingLocation.objects.create(
                            name=custom_state,
                            normalized_name=state_norm,
                            type=PendingLocation.TYPE_STATE,
                            created_by=request.user,
                            related_profile=profile,
                            status=PendingLocation.STATUS_PENDING,
                        )

                # City pending (normalized with state context to prevent collisions)
                if custom_city and custom_state:
                    city_norm = f"{_norm(custom_state)}|{_norm(custom_city)}"
                    if not PendingLocation.objects.filter(type=PendingLocation.TYPE_CITY, normalized_name=city_norm).exists():
                        PendingLocation.objects.create(
                            name=custom_city,
                            normalized_name=city_norm,
                            type=PendingLocation.TYPE_CITY,
                            created_by=request.user,
                            related_profile=profile,
                            status=PendingLocation.STATUS_PENDING,
                        )

                # Area pending (normalized with state + city context)
                if custom_area and custom_city and custom_state:
                    area_norm = f"{_norm(custom_state)}|{_norm(custom_city)}|{_norm(custom_area)}"
                    if not PendingLocation.objects.filter(type=PendingLocation.TYPE_AREA, normalized_name=area_norm).exists():
                        PendingLocation.objects.create(
                            name=custom_area,
                            normalized_name=area_norm,
                            type=PendingLocation.TYPE_AREA,
                            created_by=request.user,
                            related_profile=profile,
                            status=PendingLocation.STATUS_PENDING,
                        )
            except Exception:
                # Never break profile editing on admin-queue failures.
                pass
            
            messages.success(request, 'Profile updated successfully!')
            # Redirect back to edit page to allow continued editing
            return redirect('profiles:profile_edit')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            # Continue to render form with errors
    
    # Prepare context for template
    
    # Get all active poojas for selection (Railway, GoDaddy, VPS: include status active or null/empty)
    from django.db.models import Q
    all_poojas = Pooja.objects.filter(
        is_active=True
    ).filter(
        Q(status=Pooja.STATUS_ACTIVE) | Q(status__isnull=True) | Q(status='')
    ).select_related('pooja_category').order_by('pooja_category__display_order', 'pooja_category__name', 'name')
    
    # Group poojas by PoojaCategory (master data) for better UX
    from .services import group_poojas_by_category_for_profile
    pooja_categories = group_poojas_by_category_for_profile(all_poojas)
    
    # Ensure profile is saved before accessing M2M fields
    if profile.pk is None:
        profile.save()
    
    # Get selected poojas for this profile (only if profile has an ID)
    selected_pooja_ids = set()
    if profile.pk:
        try:
            selected_pooja_ids = set(profile.poojas_performed.values_list('id', flat=True))
        except Exception:
            # If M2M access fails, use empty set
            selected_pooja_ids = set()
    
    # Get selected languages (only if profile has an ID)
    selected_language_ids = set()
    if profile.pk:
        try:
            selected_language_ids = set(profile.languages.values_list('id', flat=True))
        except Exception:
            # If M2M access fails, use empty set
            selected_language_ids = set()
    
    # Calculate profile completion for "Complete Your Profile" message
    completion_percentage = profile.get_completion_percentage()
    is_complete = profile.is_profile_complete()
    missing_sections = profile.get_missing_required_fields()
    is_profile_approved = profile.is_profile_approved
    
    # State → City → Area: distinct states from cities (non-null). Fallback to common list if none in DB.
    from .services import get_available_states_and_preselected_state
    available_states, preselected_state = get_available_states_and_preselected_state(profile)

    # Include selected cities/areas even if they are pending/inactive so "Others" selections stay visible.
    from django.db.models import Q
    selected_city_ids = list(profile.cities_served.values_list('id', flat=True)) if profile.pk else []
    selected_area_ids = list(profile.areas_served.values_list('id', flat=True)) if profile.pk else []
    available_cities_qs = City.objects.filter(Q(is_active=True) | Q(id__in=selected_city_ids)).order_by('name')
    available_areas_qs = LocalArea.objects.filter(
        Q(is_active=True) | Q(id__in=selected_area_ids)
    ).select_related('city').order_by('city__name', 'name')

    context = {
        'current_profile': profile,
        'profile_public_id': profile.public_id,  # Use public_id in templates
        'is_profile_owner': True,
        'available_states': available_states,
        'preselected_state': preselected_state,
        'available_cities': available_cities_qs,
        'available_areas': available_areas_qs,
        'available_poojas': all_poojas,  # Keep for backward compatibility
        'pooja_categories': pooja_categories,  # Categorized poojas for better UX
        'selected_pooja_ids': selected_pooja_ids,  # Set of selected pooja IDs for quick lookup
        # Languages: Use M2M field, fallback to legacy text
        'available_languages': Language.objects.filter(is_active=True, status=Language.STATUS_ACTIVE).order_by('name'),
        'selected_language_ids': selected_language_ids,
        # For template compatibility
        'cities': available_cities_qs,
        'areas': available_areas_qs,
        'poojas': all_poojas,
        # Profile completion data for "Complete Your Profile" message
        'profile_completion_percentage': completion_percentage,
        'is_profile_complete': is_complete,
        'profile_completion_missing_sections': missing_sections,
        'is_profile_approved': is_profile_approved,
        'show_complete_profile_message': not is_complete or not is_profile_approved,  # Show message if incomplete or not approved
    }
    context.update(_pandit_profile_phone_verification_context(request, profile))
    
    return render(request, 'module4_profile/profile_edit.html', context)


@login_required
def profile_private(request, public_id=None):
    """
    Private view of Pandit's own profile.
    
    Security:
    - Only profile owner can view their private profile
    - Uses public_id (UUIDv7) to prevent unauthorized access
    - Validates user is the profile owner before showing data
    
    Shows additional information only visible to the profile owner.
    Includes profile completion, trust self-view notice, and all profile sections.
    """
    # Security: Ensure user has a pandit profile
    if not hasattr(request.user, 'pandit_profile'):
        messages.error(request, "You don't have a Pandit profile.")
        return redirect('core:home')
    
    # Security: Get profile by public_id if provided, otherwise use user's profile
    if public_id:
        # Security: Reject BIGINT IDs
        if reject_bigint_id(public_id):
            messages.error(request, "Invalid profile identifier.")
            return redirect('core:home')
        
        profile = resolve_public_id(PanditProfile, public_id)
        if not profile:
            messages.error(request, "Profile not found.")
            return redirect('core:home')
        
        # Security: Ensure user can only view their own private profile
        if profile.user != request.user:
            messages.error(request, "You don't have permission to view this profile.")
            return redirect('core:home')
    else:
        profile = request.user.pandit_profile
    
    # Security: Double-check ownership
    if profile.user != request.user:
        messages.error(request, "Access denied. You can only view your own profile.")
        return redirect('core:home')
    
    # Security: Ensure user is a pandit
    if request.user.role != 'pandit':
        messages.error(request, "Only Pandits can view private profiles.")
        return redirect('core:home')
    
    # Calculate profile completion using model methods
    completion_percentage = profile.get_completion_percentage()
    is_complete = profile.is_profile_complete()
    missing_sections = profile.get_missing_required_fields()
    
    context = {
        'current_profile': profile,
        'profile_public_id': profile.public_id,  # Use public_id in templates
        'pandit': profile,
        'user': request.user,
        'is_profile_owner': True,
        'is_pandit_owner': True,
        'profile_completion_percentage': completion_percentage,
        'profile_completion_missing_sections': missing_sections,
        'trust_signals': getattr(profile, 'trust_signals', None),  # Backend should provide
        'trust_status': getattr(profile, 'trust_status', None),  # Backend should provide
        'ratings_summary': getattr(profile, 'ratings_summary', None),  # Backend should provide
    }
    
    return render(request, 'module4_profile/profile_private.html', context)
