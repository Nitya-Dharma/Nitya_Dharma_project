"""
Review API views.

Tasks:
- 9.3: Review Submission Eligibility & Validation
- 9.4: Review Visibility & Access Rules

Backend-only APIs for review operations.
Social proof only - no ranking, trust, or search influence.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator, EmptyPage
from core.api_constants import MAX_PAGE_SIZE, DEFAULT_SEARCH_PAGE_SIZE
from core.rate_limiting import rate_limit_review_create
from .models import Review
from .models_advanced import ReviewReport
from .services import ReviewService
from .serializers import ReviewSerializer
from .permissions import (
    can_create_review,
    can_view_review,
    can_change_visibility
)
from core.public_id import resolve_public_id, reject_bigint_id
from accounts.models import User

logger = logging.getLogger(__name__)


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@require_http_methods(["POST"])
@rate_limit_review_create
def create_review(request):
    """
    Create a new review.
    
    Task 9.3: Review Submission Eligibility & Validation
    Task 9.4: Review Visibility & Access Rules
    
    POST /api/reviews/create/
    
    Body Parameters:
        - pandit_id: ID of Pandit (required)
        - rating: Rating (1-5, required)
        - review_text: Review text (required)
        - booking_intent_id: Optional Booking Intent ID
    
    Returns:
        JSON response with created review data
    
    Note:
        - Logged-in users ONLY can create
        - One review per user per pandit
        - No spam scoring
        - No ML
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Check permission
    if not can_create_review(request.user):
        return JsonResponse(
            {'error': 'You do not have permission to create reviews'},
            status=403
        )
    
    # Parse request data with NoSQL injection protection
    try:
        import json
        from core.security_utils import safe_json_loads
        from django.core.exceptions import ValidationError
        # Define allowed fields for review creation
        allowed_fields = ['pandit_public_id', 'pandit_id', 'rating', 'comment', 'anonymous']
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
    
    # Validate required fields - use public_id
    pandit_public_id = data.get('pandit_public_id') or data.get('pandit_id')  # Support both for backward compat
    if not pandit_public_id:
        return JsonResponse(
            {'error': 'pandit_public_id is required'},
            status=400
        )
    
    # Security: Reject BIGINT IDs
    if reject_bigint_id(str(pandit_public_id)):
        return JsonResponse(
            {'error': 'Invalid pandit identifier. Use public_id (UUIDv7)'},
            status=400
        )
    
    # Resolve public_id to internal ID
    pandit = resolve_public_id(User, str(pandit_public_id))
    if not pandit:
        return JsonResponse(
            {'error': 'Pandit not found'},
            status=404
        )
    
    pandit_id = pandit.id  # Use internal ID for service call
    
    rating = data.get('rating')
    if rating is None:
        return JsonResponse(
            {'error': 'rating is required'},
            status=400
        )
    
    try:
        rating = int(rating)
    except (ValueError, TypeError):
        return JsonResponse(
            {'error': 'rating must be an integer'},
            status=400
        )
    
    review_text = data.get('review_text', '').strip()
    if not review_text:
        return JsonResponse(
            {'error': 'review_text is required'},
            status=400
        )
    
    booking_intent_id = data.get('booking_intent_id')
    if booking_intent_id:
        try:
            booking_intent_id = int(booking_intent_id)
        except (ValueError, TypeError):
            booking_intent_id = None
    
    # Create review
    try:
        review = ReviewService.create_review(
            reviewer=request.user,
            pandit_id=pandit_id,
            rating=rating,
            review_text=review_text,
            booking_intent_id=booking_intent_id
        )
        
        return JsonResponse(
            ReviewSerializer.serialize(review),
            status=201
        )
    
    except ValueError as e:
        return JsonResponse(
            {'error': str(e)},
            status=400
        )
    except Exception as e:
        logger.error(f"Error creating review: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while creating review'},
            status=500
        )


@require_http_methods(["GET"])
def list_reviews_for_pandit(request, pandit_id):
    """
    List visible reviews for a Pandit.
    
    Task 9.4: Review Visibility & Access Rules
    
    GET /api/reviews/pandit/<pandit_id>/
    
    Query Parameters:
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20, max: 100)
    
    Returns:
        Paginated list of visible reviews
    
    Note:
        - Logged-in users can view visible reviews
        - Guests cannot view (handled by permission check)
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required to view reviews'},
            status=401
        )
    # Resolve pandit by public_id (URL segment)
    if reject_bigint_id(str(pandit_id)):
        return JsonResponse({'error': 'Invalid pandit identifier'}, status=400)
    pandit = resolve_public_id(User, str(pandit_id))
    if not pandit:
        return JsonResponse({'error': 'Pandit not found'}, status=404)
    
    # Get pagination parameters
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', DEFAULT_SEARCH_PAGE_SIZE))
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = DEFAULT_SEARCH_PAGE_SIZE
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE
    except (ValueError, TypeError):
        page = 1
        page_size = DEFAULT_SEARCH_PAGE_SIZE
    
    # Phase 14: Behavior analytics (review view; passive)
    try:
        from behavior_engine.trackers import track_review_view
        profile_id = getattr(getattr(pandit, 'pandit_profile', None), 'id', None)
        if profile_id is not None:
            track_review_view(request, profile_id, metadata={})
    except Exception:
        pass
    
    # Get reviews
    reviews = ReviewService.get_visible_reviews_for_pandit(pandit.id)
    
    # Pagination
    paginator = Paginator(reviews, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Serialize results
    include_metadata = request.user.role == 'admin'
    results = ReviewSerializer.serialize_list(page_obj, include_metadata)
    
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
def list_my_reviews(request):
    """
    List reviews created by the current user.
    
    Task 9.4: Review Visibility & Access Rules
    
    GET /api/reviews/my-reviews/
    
    Query Parameters:
        - visibility_state: Optional visibility state filter
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20, max: 100)
    
    Returns:
        Paginated list of reviews
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Get visibility filter
    visibility_filter = request.GET.get('visibility_state')
    if visibility_filter and visibility_filter not in dict(Review.VISIBILITY_STATE_CHOICES):
        return JsonResponse(
            {'error': 'Invalid visibility_state'},
            status=400
        )
    
    # Get pagination parameters
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', DEFAULT_SEARCH_PAGE_SIZE))
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = DEFAULT_SEARCH_PAGE_SIZE
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE
    except (ValueError, TypeError):
        page = 1
        page_size = DEFAULT_SEARCH_PAGE_SIZE
    
    # Get reviews
    reviews = ReviewService.get_reviews_by_reviewer(
        reviewer=request.user,
        visibility_state=visibility_filter
    )
    
    # Pagination
    paginator = Paginator(reviews, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Serialize results
    include_metadata = request.user.role == 'admin'
    results = ReviewSerializer.serialize_list(page_obj, include_metadata)
    
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
def get_review(request, public_id):
    """
    Get a specific review.
    
    Task 9.4: Review Visibility & Access Rules
    
    GET /api/reviews/<public_id>/
    
    Returns:
        Review data
    
    Note:
        - Permission check via can_view_review
        - Guests cannot view
        - Uses public_id (UUIDv7) for security
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required to view reviews'},
            status=401
        )
    
    # Security: Reject BIGINT IDs
    if reject_bigint_id(public_id):
        return JsonResponse(
            {'error': 'Invalid review identifier'},
            status=400
        )
    
    # Resolve public_id to internal ID
    review = resolve_public_id(Review, public_id)
    if not review:
        return JsonResponse(
            {'error': 'Review not found'},
            status=404
        )
    
    # Check permission
    if not can_view_review(request.user, review):
        return JsonResponse(
            {'error': 'You do not have permission to view this review'},
            status=403
        )
    
    include_metadata = request.user.role == 'admin'
    return JsonResponse(ReviewSerializer.serialize(review, include_metadata))


@require_http_methods(["GET"])
def get_rating_aggregation(request, pandit_public_id):
    """
    Get rating aggregation for a Pandit (display-only).
    
    Task 9.6: Ratings Aggregation & Display Inputs
    
    GET /api/reviews/pandit/<pandit_public_id>/ratings/
    
    Returns:
        Rating aggregation data (average, count, distribution)
    
    Note:
        - Display-only input for Module 10
        - No ranking meaning
        - Simple aggregation only
        - Uses public_id (UUIDv7) for security
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Security: Reject BIGINT IDs
    if reject_bigint_id(pandit_public_id):
        return JsonResponse(
            {'error': 'Invalid pandit identifier'},
            status=400
        )
    
    # Resolve public_id to internal ID
    pandit = resolve_public_id(User, pandit_public_id)
    if not pandit:
        return JsonResponse(
            {'error': 'Pandit not found'},
            status=404
        )
    
    try:
        aggregation = ReviewService.get_rating_aggregation_for_pandit(pandit.id)
        return JsonResponse(aggregation)
    except Exception as e:
        logger.error(f"Error getting rating aggregation: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while getting rating aggregation'},
            status=500
        )


@require_http_methods(["GET"])
def list_all_for_governance(request):
    """
    List all reviews for governance review (admin only).
    
    Task 9.11: Governance & Appeals Integration
    
    GET /api/reviews/governance/
    
    Query Parameters:
        - visibility_state: Optional visibility state filter
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20, max: 100)
    
    Returns:
        Paginated list of reviews
    
    Note:
        - Admin only
        - Includes all visibility states
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
    visibility_filter = request.GET.get('visibility_state')
    if visibility_filter and visibility_filter not in dict(Review.VISIBILITY_STATE_CHOICES):
        return JsonResponse(
            {'error': 'Invalid visibility_state'},
            status=400
        )
    
    # Get pagination parameters
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', DEFAULT_SEARCH_PAGE_SIZE))
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = DEFAULT_SEARCH_PAGE_SIZE
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE
    except (ValueError, TypeError):
        page = 1
        page_size = DEFAULT_SEARCH_PAGE_SIZE
    
    # Get reviews
    reviews = ReviewService.get_all_reviews_for_governance(
        visibility_state=visibility_filter
    )
    
    # Pagination
    paginator = Paginator(reviews, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Serialize results (include metadata for admin)
    results = ReviewSerializer.serialize_list(page_obj, include_metadata=True)
    
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
def change_visibility(request, public_id):
    """
    Change review visibility state (admin only).
    
    Task 9.10: Review Moderation Outcomes & Visibility States
    
    POST /api/reviews/<public_id>/change-visibility/
    
    Body Parameters:
        - visibility_state: New visibility state (visible/hidden/under_review)
        - reason: Optional reason for state change
    
    Returns:
        Updated Review data
    
    Note:
        - Admin only
        - Manual moderation only
        - No auto-removal
        - Uses public_id (UUIDv7) for security
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {'error': 'Authentication required'},
            status=401
        )
    
    # Check permission
    if not can_change_visibility(request.user):
        return JsonResponse(
            {'error': 'Admin access required'},
            status=403
        )
    
    # Security: Reject BIGINT IDs
    if reject_bigint_id(public_id):
        return JsonResponse(
            {'error': 'Invalid review identifier'},
            status=400
        )
    
    # Resolve public_id to internal ID
    review = resolve_public_id(Review, public_id)
    if not review:
        return JsonResponse(
            {'error': 'Review not found'},
            status=404
        )
    
    # Parse request data with NoSQL injection protection
    try:
        import json
        from core.security_utils import safe_json_loads
        from django.core.exceptions import ValidationError
        # Define allowed fields for visibility change
        allowed_fields = ['visibility_state']
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
    
    new_state = data.get('visibility_state', '').strip()
    if not new_state:
        return JsonResponse(
            {'error': 'visibility_state is required'},
            status=400
        )
    
    # PART 3 HARDENING: Explicit ownership assertion for write path (defense-in-depth)
    # Admin-only endpoint, but explicit check for auditability
    from django.core.exceptions import PermissionDenied
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Explicit authorization check failed: admin required")
    
    # PART 3 HARDENING: Explicit state transition validation
    from core.api_constants import REVIEW_VISIBILITY_TRANSITIONS
    current_state = review.visibility_state
    allowed_next_states = REVIEW_VISIBILITY_TRANSITIONS.get(current_state, [])
    if new_state not in allowed_next_states:
        from django.core.exceptions import ValidationError
        raise ValidationError(f"Invalid visibility transition: {current_state} -> {new_state}")
    
    reason = data.get('reason', '').strip()
    
    try:
        updated_review = ReviewService.change_visibility_state(
            review_id=review.id,
            new_state=new_state,
            admin_user=request.user,
            reason=reason
        )
        return JsonResponse(ReviewSerializer.serialize(updated_review, include_metadata=True))
    
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
        logger.error(f"Error changing review visibility: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while changing review visibility'},
            status=500
        )


# CSRF enforced for same-origin browser; frontend must send X-CSRFToken header or csrfmiddlewaretoken in form
@csrf_protect
@require_http_methods(["POST"])
def report_review(request, public_id):
    """
    Report a review for abuse.
    
    Task 9.9: Review Reporting Rules
    
    POST /api/reviews/<public_id>/report/
    
    Body Parameters:
        - reason: Reason for reporting (required)
    
    Returns:
        Updated Review data
    
    Note:
        - Users and Pandits may report reviews
        - Reporting ≠ deletion
        - Governance decides outcome (Module 11)
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
            {'error': 'Invalid review identifier'},
            status=400
        )
    
    # Resolve public_id to internal ID
    review = resolve_public_id(Review, public_id)
    if not review:
        return JsonResponse(
            {'error': 'Review not found'},
            status=404
        )
    
    # Parse request data with NoSQL injection protection
    try:
        import json
        from core.security_utils import safe_json_loads
        from django.core.exceptions import ValidationError
        # Define allowed fields for review reporting
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
    
    # One-report-per-user: if this user already reported this review, return success (same response shape)
    if ReviewReport.objects.filter(review=review, user=request.user).exists():
        include_metadata = request.user.role == 'admin'
        return JsonResponse(ReviewSerializer.serialize(review, include_metadata))
    
    try:
        updated_review = ReviewService.report_review(
            review_id=review.id,
            reporter=request.user,
            reason=reason
        )
        # Track reporter so we enforce one report per user on future calls
        ReviewReport.objects.get_or_create(
            review=review,
            user=request.user,
            defaults={'reason': ReviewReport.OTHER, 'reason_text': reason}
        )
        include_metadata = request.user.role == 'admin'
        return JsonResponse(ReviewSerializer.serialize(updated_review, include_metadata))
    
    except ValueError as e:
        return JsonResponse(
            {'error': str(e)},
            status=400
        )
    except Exception as e:
        logger.error(f"Error reporting review: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while reporting review'},
            status=500
        )
