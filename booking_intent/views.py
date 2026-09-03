"""
Booking Intent API views.

Tasks:
- 8.10: Booking Intent APIs & Services
- 8.13: Security & Permission Enforcement

Backend-only APIs for booking intent operations.
No mutations beyond status changes.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator, EmptyPage
from django.utils.dateparse import parse_date, parse_time
from .models import BookingIntent
from .services import BookingIntentService
from .serializers import BookingIntentSerializer
from .permissions import (
    can_create_intent,
    can_view_intent,
    can_cancel_intent,
    can_mark_as_viewed,
    can_flag_intent
)
from core.public_id import resolve_public_id, reject_bigint_id
from core.rate_limiting import rate_limit_booking_intent_create
from accounts.models import User

logger = logging.getLogger(__name__)


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@require_http_methods(["POST"])
@rate_limit_booking_intent_create
def create_intent(request):
    """
    Create a new booking intent.
    
    Task 8.10: Booking Intent APIs & Services
    Task 8.13: Security & Permission Enforcement
    
    POST /api/booking-intent/create/
    
    Body Parameters:
        - pandit_id: ID of Pandit (required)
        - optional_requested_date: Optional date (YYYY-MM-DD)
        - optional_requested_time: Optional time (HH:MM:SS)
        - message: Optional message (max 500 chars)
    
    Returns:
        JSON response with created intent data
    
    Note:
        - Logged-in users ONLY can create
        - No slot reservation
        - No availability validation beyond read
        - No booking confirmation
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Check permission
    if not can_create_intent(request.user):
        return JsonResponse(
            {'error': 'You do not have permission to create booking intent'},
            status=403
        )
    
    # Parse request data with NoSQL injection protection
    try:
        import json
        from core.security_utils import safe_json_loads
        from django.core.exceptions import ValidationError
        # Define allowed fields for booking intent creation
        allowed_fields = ['pandit_id', 'optional_requested_date', 'optional_requested_time', 'message']
        data = safe_json_loads(request.body, allowed_fields=allowed_fields)
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )
    except ValidationError as e:
        return JsonResponse(
            {'error': 'Invalid payload', 'message': str(e)},
            status=400
        )
    
    # Validate required fields
    pandit_id = data.get('pandit_id')
    if not pandit_id:
        return JsonResponse(
            {'error': 'pandit_id is required'},
            status=400
        )
    
    try:
        pandit_id = int(pandit_id)
    except (ValueError, TypeError):
        return JsonResponse(
            {'error': 'Invalid pandit_id'},
            status=400
        )
    
    # Parse optional fields
    optional_requested_date = None
    if data.get('optional_requested_date'):
        optional_requested_date = parse_date(data['optional_requested_date'])
        if optional_requested_date is None:
            return JsonResponse(
                {'error': 'Invalid optional_requested_date format. Use YYYY-MM-DD'},
                status=400
            )
    
    optional_requested_time = None
    if data.get('optional_requested_time'):
        optional_requested_time = parse_time(data['optional_requested_time'])
        if optional_requested_time is None:
            return JsonResponse(
                {'error': 'Invalid optional_requested_time format. Use HH:MM:SS'},
                status=400
            )
    
    message = data.get('message', '')
    if message and len(message) > 500:
        return JsonResponse(
            {'error': 'Message must be 500 characters or less'},
            status=400
        )
    
    # Create intent
    try:
        intent = BookingIntentService.create_intent(
            requester=request.user,
            pandit_id=pandit_id,
            optional_requested_date=optional_requested_date,
            optional_requested_time=optional_requested_time,
            message=message,
            request=request,
        )
        # Phase 14: Behavior analytics (conversion signal; passive)
        try:
            from behavior_engine.trackers import track_booking_intent
            profile_id = getattr(getattr(intent.pandit, 'pandit_profile', None), 'id', None)
            if profile_id is not None:
                track_booking_intent(request, profile_id, metadata={})
        except Exception:
            pass
        # Notify the pandit about the new booking intent
        try:
            from notifications.services import NotificationService
            from notifications.constants import NOTIFICATION_TYPE_BOOKING_INTENT
            requester_name = (getattr(intent.requester, 'get_full_name', None) and intent.requester.get_full_name()) or getattr(intent.requester, 'email', 'A user')
            NotificationService.create_notification(
                recipient=intent.pandit,
                notification_type=NOTIFICATION_TYPE_BOOKING_INTENT,
                source_module='booking_intent',
                payload={
                    'title': 'New booking intent',
                    'message': f'{requester_name} sent you a booking enquiry.',
                    'booking_intent_public_id': getattr(intent, 'public_id', None) or str(intent.id),
                },
            )
        except Exception as e:
            logger.warning(f"Could not create pandit notification for booking intent: {e}")
        return JsonResponse(
            BookingIntentSerializer.serialize(intent),
            status=201
        )
    
    except ValueError as e:
        return JsonResponse(
            {'error': str(e)},
            status=400
        )
    except Exception as e:
        logger.error(f"Error creating booking intent: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while creating booking intent'},
            status=500
        )


@require_http_methods(["GET"])
def list_my_intents(request):
    """
    List booking intents created by the current user.
    
    Task 8.10: Booking Intent APIs & Services
    Task 8.13: Security & Permission Enforcement
    
    GET /api/booking-intent/my-intents/
    
    Query Parameters:
        - status: Optional status filter
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20, max: 100)
    
    Returns:
        Paginated list of booking intents
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Get status filter
    status_filter = request.GET.get('status')
    if status_filter and status_filter not in dict(BookingIntent.STATUS_CHOICES):
        return JsonResponse(
            {'error': 'Invalid status'},
            status=400
        )
    
    # Get pagination parameters with hard cap (PART 3 hardening)
    from core.api_constants import MAX_PAGE_SIZE, DEFAULT_SEARCH_PAGE_SIZE
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', DEFAULT_SEARCH_PAGE_SIZE))
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = DEFAULT_SEARCH_PAGE_SIZE
        # Enforce non-bypassable maximum
        page_size = min(page_size, MAX_PAGE_SIZE)
    except (ValueError, TypeError):
        page = 1
        page_size = DEFAULT_SEARCH_PAGE_SIZE
    
    # Get intents
    intents = BookingIntentService.get_intents_for_requester(
        requester=request.user,
        status=status_filter
    )
    
    # Pagination
    paginator = Paginator(intents, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Serialize results
    results = BookingIntentSerializer.serialize_list(page_obj)
    
    return JsonResponse({
        'results': results,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })


@require_http_methods(["GET"])
def list_received_intents(request):
    """
    List booking intents received by the current Pandit.
    
    Task 8.10: Booking Intent APIs & Services
    Task 8.13: Security & Permission Enforcement
    
    GET /api/booking-intent/received-intents/
    
    Query Parameters:
        - status: Optional status filter
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20, max: 100)
    
    Returns:
        Paginated list of booking intents
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Verify user is Pandit
    if request.user.role != 'pandit':
        return JsonResponse(
            {'error': 'Only Pandits can view received intents'},
            status=403
        )
    
    # Get status filter
    status_filter = request.GET.get('status')
    if status_filter and status_filter not in dict(BookingIntent.STATUS_CHOICES):
        return JsonResponse(
            {'error': 'Invalid status'},
            status=400
        )
    
    # Get pagination parameters with hard cap (PART 3 hardening)
    from core.api_constants import MAX_PAGE_SIZE, DEFAULT_SEARCH_PAGE_SIZE
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', DEFAULT_SEARCH_PAGE_SIZE))
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = DEFAULT_SEARCH_PAGE_SIZE
        # Enforce non-bypassable maximum
        page_size = min(page_size, MAX_PAGE_SIZE)
    except (ValueError, TypeError):
        page = 1
        page_size = DEFAULT_SEARCH_PAGE_SIZE
    
    # Get intents
    intents = BookingIntentService.get_intents_for_pandit(
        pandit=request.user,
        status=status_filter
    )
    
    # Pagination
    paginator = Paginator(intents, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Serialize results
    results = BookingIntentSerializer.serialize_list(page_obj)
    
    return JsonResponse({
        'results': results,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })


@require_http_methods(["GET"])
def get_intent(request, public_id):
    """
    Get a specific booking intent.
    
    Task 8.10: Booking Intent APIs & Services
    Task 8.13: Security & Permission Enforcement
    
    GET /api/booking-intent/<public_id>/
    
    Returns:
        BookingIntent data
    
    Note:
        - Only requester, pandit, or admin can view
        - No cross-user visibility
        - Uses public_id (UUIDv7) for security
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Security: Reject BIGINT IDs
    if reject_bigint_id(public_id):
        return JsonResponse(
            {'error': 'Invalid intent identifier'},
            status=400
        )
    
    # Resolve public_id to internal ID
    intent = resolve_public_id(BookingIntent, public_id)
    if not intent:
        return JsonResponse(
            {'error': 'Booking intent not found'},
            status=404
        )
    
    # Check permission
    if not can_view_intent(request.user, intent):
        return JsonResponse(
            {'error': 'You do not have permission to view this intent'},
            status=403
        )
    
    # PART 3 HARDENING: Explicit ownership assertion (defense-in-depth)
    # Ownership is already enforced via can_view_intent, but make it explicit
    from django.core.exceptions import PermissionDenied
    if intent.requester_id != request.user.id and intent.pandit_id != request.user.id:
        # Admin check is handled by can_view_intent, but explicit check here for auditability
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied("Explicit ownership check failed")
    
    return JsonResponse(BookingIntentSerializer.serialize(intent))


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@require_http_methods(["POST"])
def cancel_intent(request, public_id):
    """
    Cancel a booking intent.
    
    Task 8.10: Booking Intent APIs & Services
    Task 8.13: Security & Permission Enforcement
    
    POST /api/booking-intent/<public_id>/cancel/
    
    Returns:
        Updated BookingIntent data
    
    Note:
        - Only requester can cancel
        - Soft cancel (status change, no delete)
        - Uses public_id (UUIDv7) for security
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Security: Reject BIGINT IDs
    if reject_bigint_id(public_id):
        return JsonResponse(
            {'error': 'Invalid intent identifier'},
            status=400
        )
    
    # Resolve public_id to internal ID
    intent = resolve_public_id(BookingIntent, public_id)
    if not intent:
        return JsonResponse(
            {'error': 'Booking intent not found'},
            status=404
        )
    
    # Check permission
    if not can_cancel_intent(request.user, intent):
        return JsonResponse(
            {'error': 'You do not have permission to cancel this intent'},
            status=403
        )
    
    # PART 3 HARDENING: Explicit ownership assertion for write path (defense-in-depth)
    from django.core.exceptions import PermissionDenied
    if intent.requester_id != request.user.id:
        raise PermissionDenied("Explicit ownership check failed: only requester can cancel")
    
    try:
        updated_intent = BookingIntentService.cancel_intent(intent.id, request.user)
        return JsonResponse(BookingIntentSerializer.serialize(updated_intent))
    
    except ValueError as e:
        return JsonResponse(
            {'error': str(e)},
            status=400
        )
    except PermissionError as e:
        return JsonResponse(
            {'error': str(e)},
            status=403
        )
    except Exception as e:
        logger.error(f"Error cancelling booking intent: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while cancelling booking intent'},
            status=500
        )


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@require_http_methods(["POST"])
def mark_as_viewed(request, public_id):
    """
    Mark a booking intent as viewed by Pandit.
    
    Task 8.10: Booking Intent APIs & Services
    Task 8.13: Security & Permission Enforcement
    
    POST /api/booking-intent/<public_id>/mark-viewed/
    
    Returns:
        Updated BookingIntent data
    
    Note:
        - Only pandit can mark as viewed
        - Uses public_id (UUIDv7) for security
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Security: Reject BIGINT IDs
    if reject_bigint_id(public_id):
        return JsonResponse(
            {'error': 'Invalid intent identifier'},
            status=400
        )
    
    # Resolve public_id to internal ID
    intent = resolve_public_id(BookingIntent, public_id)
    if not intent:
        return JsonResponse(
            {'error': 'Booking intent not found'},
            status=404
        )
    
    # Check permission
    if not can_mark_as_viewed(request.user, intent):
        return JsonResponse(
            {'error': 'You do not have permission to mark this intent as viewed'},
            status=403
        )
    
    try:
        updated_intent = BookingIntentService.mark_as_viewed(intent.id, request.user)
        unread_count = BookingIntent.objects.filter(
            pandit=request.user,
            status=BookingIntent.STATUS_SUBMITTED
        ).count()
        data = BookingIntentSerializer.serialize(updated_intent)
        data["success"] = True
        data["unread_count"] = unread_count
        return JsonResponse(data)

    except ValueError as e:
        return JsonResponse(
            {'error': str(e)},
            status=400
        )
    except PermissionError as e:
        return JsonResponse(
            {'error': str(e)},
            status=403
        )
    except Exception as e:
        logger.error(f"Error marking intent as viewed: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while marking intent as viewed'},
            status=500
        )


@require_http_methods(["GET"])
def list_all_for_governance(request):
    """
    List all booking intents for governance review (admin only).
    
    Task 8.12: Governance Hooks & Reporting
    Task 8.13: Security & Permission Enforcement
    
    GET /api/booking-intent/governance/
    
    Query Parameters:
        - status: Optional status filter
        - is_flagged: Optional flag filter (true/false)
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20, max: 100)
    
    Returns:
        Paginated list of booking intents
    
    Note:
        - Admin only
        - Read-only visibility
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Verify admin
    if request.user.role != 'admin':
        return JsonResponse(
            {'error': 'Admin access required'},
            status=403
        )
    
    # Get filters
    status_filter = request.GET.get('status')
    if status_filter and status_filter not in dict(BookingIntent.STATUS_CHOICES):
        return JsonResponse(
            {'error': 'Invalid status'},
            status=400
        )
    
    is_flagged_filter = None
    if request.GET.get('is_flagged') is not None:
        is_flagged_filter = request.GET.get('is_flagged').lower() == 'true'
    
    # Get pagination parameters with hard cap (PART 3 hardening)
    from core.api_constants import MAX_PAGE_SIZE, DEFAULT_SEARCH_PAGE_SIZE
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', DEFAULT_SEARCH_PAGE_SIZE))
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = DEFAULT_SEARCH_PAGE_SIZE
        # Enforce non-bypassable maximum
        page_size = min(page_size, MAX_PAGE_SIZE)
    except (ValueError, TypeError):
        page = 1
        page_size = DEFAULT_SEARCH_PAGE_SIZE
    
    # Get intents
    intents = BookingIntentService.get_all_intents_for_governance(
        status=status_filter,
        is_flagged=is_flagged_filter
    )
    
    # Pagination
    paginator = Paginator(intents, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Serialize results
    results = BookingIntentSerializer.serialize_list(page_obj)
    
    return JsonResponse({
        'results': results,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@require_http_methods(["POST"])
def flag_intent(request, public_id):
    """
    Flag a booking intent for governance review (admin only).
    
    Task 8.12: Governance Hooks & Reporting
    Task 8.13: Security & Permission Enforcement
    
    POST /api/booking-intent/<public_id>/flag/
    
    Body Parameters:
        - reason: Reason for flagging (required)
    
    Returns:
        Updated BookingIntent data
    
    Note:
        - Admin only
        - No automated moderation
        - Manual flagging only
        - Uses public_id (UUIDv7) for security
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Check permission
    if not can_flag_intent(request.user):
        return JsonResponse(
            {'error': 'Admin access required'},
            status=403
        )
    
    # Security: Reject BIGINT IDs
    if reject_bigint_id(public_id):
        return JsonResponse(
            {'error': 'Invalid intent identifier'},
            status=400
        )
    
    # Resolve public_id to internal ID
    intent = resolve_public_id(BookingIntent, public_id)
    if not intent:
        return JsonResponse(
            {'error': 'Booking intent not found'},
            status=404
        )
    
    # Parse request data with NoSQL injection protection
    try:
        import json
        from core.security_utils import safe_json_loads
        from django.core.exceptions import ValidationError
        # Define allowed fields for booking intent cancellation
        allowed_fields = ['reason']
        data = safe_json_loads(request.body, allowed_fields=allowed_fields)
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )
    except ValidationError as e:
        return JsonResponse(
            {'error': 'Invalid payload', 'message': str(e)},
            status=400
        )
    
    reason = data.get('reason', '').strip()
    if not reason:
        return JsonResponse(
            {'error': 'reason is required'},
            status=400
        )
    
    try:
        updated_intent = BookingIntentService.flag_intent(intent.id, reason, request.user)
        return JsonResponse(BookingIntentSerializer.serialize(updated_intent))
    
    except ValueError as e:
        return JsonResponse(
            {'error': str(e)},
            status=400
        )
    except PermissionError as e:
        return JsonResponse(
            {'error': str(e)},
            status=403
        )
    except Exception as e:
        logger.error(f"Error flagging booking intent: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while flagging booking intent'},
            status=500
        )
