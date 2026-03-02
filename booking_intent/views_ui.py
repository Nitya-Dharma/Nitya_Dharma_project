"""
Booking Intent UI views (template-based).
These views render HTML templates for booking intent functionality.
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import User
from .models import BookingIntent
from .services import BookingIntentService


@login_required
def booking_history(request):
    """
    User booking intent history page (HTML template).
    
    Renders booking intent history in HTML format.
    Shows only the logged-in user's own booking intents.
    """
    # Get status filter from query string
    status_filter = request.GET.get('status')
    if status_filter and status_filter not in dict(BookingIntent.STATUS_CHOICES):
        status_filter = None
    
    # Get booking intents for the current user
    # BookingIntentService returns QuerySet, we can add additional prefetch if needed
    intents = BookingIntentService.get_intents_for_requester(
        requester=request.user,
        status=status_filter
    ).prefetch_related('pandit__pandit_profile')
    
    # Pagination
    from django.core.paginator import Paginator, EmptyPage
    page = int(request.GET.get('page', 1))
    page_size = 20
    paginator = Paginator(intents, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'booking_intents': page_obj,
        'pagination': {
            'page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        },
        'current_status_filter': status_filter,
        'status_choices': BookingIntent.STATUS_CHOICES,
        'user_role': 'user',  # Set user_role for empty state message
    }
    
    return render(request, 'module8_booking/booking_user_history.html', context)


@login_required
def booking_inbox(request):
    """
    Pandit booking intent inbox page (HTML template).
    
    Renders booking intents received by the current Pandit.
    Only accessible to Pandits.
    """
    # Verify user is Pandit
    if request.user.role != 'pandit':
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Only Pandits can access this page.")
    
    # Get status filter from query string
    status_filter = request.GET.get('status')
    if status_filter and status_filter not in dict(BookingIntent.STATUS_CHOICES):
        status_filter = None
    
    # Get booking intents for the current Pandit
    # BookingIntentService returns QuerySet, we can add additional prefetch if needed
    intents = BookingIntentService.get_intents_for_pandit(
        pandit=request.user,
        status=status_filter
    ).prefetch_related('requester__pandit_profile')
    
    # Pagination
    from django.core.paginator import Paginator, EmptyPage
    page = int(request.GET.get('page', 1))
    page_size = 20
    paginator = Paginator(intents, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'received_intents': page_obj,  # Template expects 'received_intents'
        'booking_intents': page_obj,  # Keep for backward compatibility
        'pagination': {
            'page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        },
        'current_status_filter': status_filter,
        'status_choices': BookingIntent.STATUS_CHOICES,
        'is_pandit_inbox': True,
    }
    
    return render(request, 'module8_booking/booking_pandit_inbox.html', context)


@login_required
def create_booking_intent_form(request, pandit_public_id):
    """
    Booking intent creation form page (HTML template).
    
    Handles both GET (show form) and POST (process form submission).
    
    Args:
        pandit_public_id: Public ID (UUIDv7) of the Pandit user
    """
    from core.public_id import reject_bigint_id, resolve_public_id
    from profiles.models import PanditProfile
    
    # Handle both UUIDv7 (public_id) and BIGINT (backward compatibility)
    pandit_profile = None
    
    # Check if it's a BIGINT ID (backward compatibility)
    if reject_bigint_id(pandit_public_id):
        # It's a BIGINT ID - try to get by user ID (backward compatibility)
        try:
            user_id = int(pandit_public_id)
            # Get user first, then profile
            pandit_user = get_object_or_404(User, pk=user_id, role='pandit', status='active', is_active=True)
            if hasattr(pandit_user, 'pandit_profile'):
                pandit_profile = pandit_user.pandit_profile
            else:
                from django.http import Http404
                raise Http404("Pandit profile not found.")
        except (ValueError, TypeError):
            from django.http import HttpResponseBadRequest
            return HttpResponseBadRequest("Invalid Pandit identifier.")
    else:
        # It's a UUIDv7 - resolve by public_id
        pandit_profile = resolve_public_id(PanditProfile, pandit_public_id)
    
    if not pandit_profile:
        from django.http import Http404
        raise Http404("Pandit profile not found.")
    
    # Get the Pandit user from the profile
    pandit = pandit_profile.user
    
    # Verify it's a pandit and active
    if pandit.role != 'pandit' or pandit.status != 'active' or not pandit.is_active:
        from django.http import Http404
        raise Http404("Pandit not found or inactive.")
    
    # Check if Pandit has a profile
    if not hasattr(pandit, 'pandit_profile'):
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound("Pandit profile not found.")
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        from django.http import JsonResponse
        from django.views.decorators.csrf import csrf_exempt
        from .services import BookingIntentService
        from .permissions import can_create_intent
        
        # Check permission
        if not can_create_intent(request.user):
            from django.contrib import messages
            messages.error(request, 'You do not have permission to create a booking intent.')
            # Fall through to render form again with error
        
        # Get form data (support both field names for compatibility)
        optional_requested_date = request.POST.get('optional_requested_date') or request.POST.get('preferred_date')
        optional_requested_time = request.POST.get('optional_requested_time') or request.POST.get('preferred_time')
        message = request.POST.get('message', '').strip()
        pooja_id = request.POST.get('pooja_id', '').strip()
        location = request.POST.get('location', '').strip()
        user_mobile_number = request.POST.get('user_mobile_number', '').strip()
        
        # Build message with pooja and location if provided (since model doesn't have these fields yet)
        full_message_parts = []
        if message:
            full_message_parts.append(message)
        if pooja_id:
            try:
                from masterdata.models import Pooja
                pooja = Pooja.objects.get(id=int(pooja_id), status=Pooja.STATUS_ACTIVE)
                full_message_parts.append(f"\n\nPreferred Pooja: {pooja.name}")
            except (ValueError, Pooja.DoesNotExist):
                pass  # Ignore invalid pooja
        if location:
            full_message_parts.append(f"\n\nLocation: {location}")
        
        # Combine message parts (truncate to 500 chars)
        combined_message = ''.join(full_message_parts)[:500] if full_message_parts else None
        
        # Parse dates/times
        parsed_date = None
        parsed_time = None
        if optional_requested_date:
            from django.utils.dateparse import parse_date
            parsed_date = parse_date(optional_requested_date)
        if optional_requested_time:
            from django.utils.dateparse import parse_time
            parsed_time = parse_time(optional_requested_time)
        
        # Create booking intent
        try:
            # Convert date/time objects to strings if they exist
            date_str = None
            if optional_requested_date:
                # If already parsed, format it; otherwise use as-is
                if parsed_date:
                    date_str = parsed_date.strftime('%Y-%m-%d')
                else:
                    date_str = optional_requested_date
            
            time_str = None
            if optional_requested_time:
                # If already parsed, format it; otherwise use as-is
                if parsed_time:
                    time_str = parsed_time.strftime('%H:%M:%S')
                else:
                    time_str = optional_requested_time
            
            intent = BookingIntentService.create_intent(
                requester=request.user,
                pandit_id=pandit.id,
                optional_requested_date=date_str,
                optional_requested_time=time_str,
                message=combined_message,
                user_mobile_number=user_mobile_number
            )
            
            # Redirect to success page or back to profile
            from django.shortcuts import redirect
            from django.contrib import messages
            messages.success(request, 'Your booking enquiry has been sent successfully to the Pandit!')
            # Use public_id for redirect (secure)
            return redirect('profiles:profile_public', public_id=pandit.pandit_profile.public_id)
        except ValueError as e:
            from django.contrib import messages
            messages.error(request, f'Validation error: {str(e)}')
            # Fall through to render form again with error
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Error creating booking intent: {str(e)}')
            # Fall through to render form again with error
    
    # Handle GET request (show form)
    # Get poojas for the form dropdown
    from masterdata.models import Pooja
    poojas = Pooja.objects.filter(status=Pooja.STATUS_ACTIVE).order_by('category', 'name')
    
    context = {
        'pandit': pandit.pandit_profile,
        'pandit_user': pandit,  # Also provide User object for ID access
        'user': request.user,
        'poojas': poojas,  # For pooja dropdown in form
        'form': None,  # No form object needed for simple template
    }
    
    return render(request, 'module8_booking/booking_form.html', context)

