"""
Advanced Page Review System Views.

Includes helpful voting, enhanced reporting, and star breakdown analytics for temple reviews.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count
from .models import PageReview
from .models_page_review_advanced import PageReviewHelpfulVote, PageReviewReport
from core.public_id import resolve_public_id, reject_bigint_id

logger = logging.getLogger(__name__)


@csrf_protect
@require_http_methods(["POST"])
@login_required
def vote_page_review_helpful(request, review_id):
    """
    Mark a page review as helpful.
    
    POST /api/pages/review/<id>/helpful/
    
    Returns:
        JSON response with updated helpful_count
    """
    try:
        review_id_int = int(review_id)
        review = PageReview.objects.get(id=review_id_int)
    except (ValueError, PageReview.DoesNotExist):
        return JsonResponse(
            {'error': 'Review not found'},
            status=404
        )
    
    # Check if user already voted
    existing_vote = PageReviewHelpfulVote.objects.filter(
        review=review,
        user=request.user
    ).first()
    
    if existing_vote:
        return JsonResponse(
            {'error': 'You have already marked this review as helpful'},
            status=400
        )
    
    # Prevent voting on own review
    if review.user_id and review.user_id == request.user.id:
        return JsonResponse(
            {'error': 'You cannot vote on your own review'},
            status=400
        )
    
    # Create vote (this will auto-increment helpful_count via save() method)
    try:
        with transaction.atomic():
            vote = PageReviewHelpfulVote.objects.create(
                review=review,
                user=request.user
            )
            # Refresh review to get updated count
            review.refresh_from_db()
            
            return JsonResponse({
                'success': True,
                'helpful_count': review.helpful_count,
                'message': 'Review marked as helpful'
            })
    except Exception as e:
        logger.error(f"Error voting helpful: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while voting'},
            status=500
        )


@csrf_protect
@require_http_methods(["POST"])
@login_required
def report_page_review_advanced(request, public_id):
    """
    Report a page review with detailed tracking.
    
    POST /api/pages/review/<public_id>/report/
    
    Body Parameters:
        - reason: One of 'spam', 'inappropriate', 'fake', 'offensive', 'other'
        - reason_text: Optional additional details
    
    Returns:
        JSON response with report status
    """
    # Security: Reject BIGINT IDs
    if reject_bigint_id(public_id):
        return JsonResponse(
            {'error': 'Invalid review identifier'},
            status=400
        )
    
    # Resolve public_id to internal ID
    review = resolve_public_id(PageReview, public_id)
    if not review:
        return JsonResponse(
            {'error': 'Review not found'},
            status=404
        )
    
    # Parse request data
    try:
        import json
        from core.security_utils import safe_json_loads
        allowed_fields = ['reason', 'reason_text']
        data = safe_json_loads(request.body, allowed_fields=allowed_fields)
    except json.JSONDecodeError:
        return JsonResponse(
            {'error': 'Invalid JSON'},
            status=400
        )
    
    reason = data.get('reason', 'other')
    reason_text = data.get('reason_text', '').strip()
    
    # Validate reason
    valid_reasons = [choice[0] for choice in PageReviewReport.REASON_CHOICES]
    if reason not in valid_reasons:
        reason = 'other'
    
    # Check if user already reported
    existing_report = PageReviewReport.objects.filter(
        review=review,
        user=request.user
    ).first()
    
    if existing_report:
        return JsonResponse(
            {'error': 'You have already reported this review'},
            status=400
        )
    
    # Prevent reporting own review
    if review.user_id and review.user_id == request.user.id:
        return JsonResponse(
            {'error': 'You cannot report your own review'},
            status=400
        )
    
    # Create report (this will auto-increment reported_count and auto-hide if threshold reached)
    try:
        with transaction.atomic():
            report = PageReviewReport.objects.create(
                review=review,
                user=request.user,
                reason=reason,
                reason_text=reason_text
            )
            # Refresh review to get updated counts
            review.refresh_from_db()
            
            return JsonResponse({
                'success': True,
                'reported_count': review.reported_count,
                'is_hidden': review.is_hidden,
                'message': 'Review reported successfully'
            })
    except Exception as e:
        logger.error(f"Error reporting review: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while reporting review'},
            status=500
        )


def get_page_star_breakdown(page_id):
    """
    Calculate star breakdown for a page/temple.
    
    Returns:
        dict with rating statistics
    """
    reviews = PageReview.objects.filter(
        page_id=page_id,
        visibility_state=PageReview.VISIBLE,
        is_hidden=False
    )
    
    total = reviews.count()
    
    if total == 0:
        return {
            'total': 0,
            'average': 0.0,
            'breakdown': {
                '5': {'count': 0, 'percentage': 0},
                '4': {'count': 0, 'percentage': 0},
                '3': {'count': 0, 'percentage': 0},
                '2': {'count': 0, 'percentage': 0},
                '1': {'count': 0, 'percentage': 0},
            }
        }
    
    # Calculate average
    average = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
    
    # Count by rating
    breakdown = {}
    for rating in [5, 4, 3, 2, 1]:
        count = reviews.filter(rating=rating).count()
        percentage = round((count / total) * 100, 1) if total > 0 else 0
        breakdown[str(rating)] = {
            'count': count,
            'percentage': percentage
        }
    
    return {
        'total': total,
        'average': round(average, 1),
        'breakdown': breakdown
    }













