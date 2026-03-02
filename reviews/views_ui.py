"""
Review UI views (template-based).

These views render HTML templates for review functionality.
End User Reviews for Pandits - UI implementation.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from django.http import JsonResponse
from accounts.models import User
from profiles.models import PanditProfile
from .models import Review
from .services import ReviewService
from .permissions import can_create_review, can_view_review
from core.public_id import resolve_public_id, reject_bigint_id


def pandit_reviews(request, pandit_public_id):
    """
    Display reviews for a Pandit (public view).
    
    Shows all visible reviews for a specific Pandit.
    Publicly accessible - no authentication required.
    """
    # Security: Reject BIGINT IDs
    if reject_bigint_id(pandit_public_id):
        messages.error(request, 'Invalid pandit identifier.')
        return redirect('search:search_results')
    
    # Resolve public_id to internal ID
    pandit_user = resolve_public_id(User, pandit_public_id)
    if not pandit_user:
        messages.error(request, 'Pandit not found.')
        return redirect('search:search_results')
    
    # Get pandit profile
    try:
        pandit = pandit_user.pandit_profile
    except PanditProfile.DoesNotExist:
        messages.error(request, 'Pandit profile not found.')
        return redirect('search:search_results')
    
    # Get visible reviews
    reviews = ReviewService.get_visible_reviews_for_pandit(pandit_user.id)
    
    # Pagination
    paginator = Paginator(reviews, 10)
    page = int(request.GET.get('page', 1))
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Check if current user can submit review
    can_submit = False
    has_reviewed = False
    if request.user.is_authenticated:
        can_submit = can_create_review(request.user)
        has_reviewed = Review.objects.filter(
            user=request.user,
            pandit=pandit_user,
            visibility_state=Review.VISIBLE
        ).exists()
    
    # Get rating aggregation
    rating_aggregation = ReviewService.get_rating_aggregation_for_pandit(pandit_user.id)
    
    # Get star breakdown
    from .views_advanced import get_star_breakdown
    star_breakdown = get_star_breakdown(pandit_user.id)
    
    # Check which reviews user has voted helpful
    user_helpful_votes = set()
    if request.user.is_authenticated:
        from .models_advanced import ReviewHelpfulVote
        user_helpful_votes = set(
            ReviewHelpfulVote.objects.filter(
                user=request.user,
                review_id__in=[r.id for r in page_obj]
            ).values_list('review_id', flat=True)
        )
    
    context = {
        'pandit': pandit,
        'pandit_user': pandit_user,
        'reviews': page_obj,
        'pagination': {
            'page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
            'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
        },
        'can_submit': can_submit and not has_reviewed,
        'has_reviewed': has_reviewed,
        'rating_aggregation': rating_aggregation,
        'star_breakdown': star_breakdown,
        'user_helpful_votes': user_helpful_votes,
    }
    
    return render(request, 'module9_reviews/pandit_reviews.html', context)


@login_required
def submit_review(request, pandit_public_id):
    """
    Submit a review for a Pandit (End User only).
    
    GET: Show review form
    POST: Process review submission
    """
    # Security: Reject BIGINT IDs
    if reject_bigint_id(pandit_public_id):
        messages.error(request, 'Invalid pandit identifier.')
        return redirect('search:search_results')
    
    # Check permission
    if not can_create_review(request.user):
        messages.error(request, 'Only End Users can submit reviews.')
        return redirect('search:search_results')
    
    # Resolve public_id to internal ID
    pandit_user = resolve_public_id(User, pandit_public_id)
    if not pandit_user:
        messages.error(request, 'Pandit not found.')
        return redirect('search:search_results')
    
    # Get pandit profile
    try:
        pandit = pandit_user.pandit_profile
    except PanditProfile.DoesNotExist:
        messages.error(request, 'Pandit profile not found.')
        return redirect('search:search_results')
    
    # Check if user already reviewed
    existing_review = Review.objects.filter(
        user=request.user,
        pandit=pandit_user
    ).first()
    
    if existing_review:
        messages.info(request, 'You have already reviewed this Pandit.')
        return redirect('reviews:pandit_reviews', pandit_public_id=pandit_user.public_id)
    
    # Prevent self-review
    if request.user.id == pandit_user.id:
        messages.error(request, 'You cannot review yourself.')
        return redirect('reviews:pandit_reviews', pandit_public_id=pandit_user.public_id)
    
    if request.method == 'POST':
        # Double-check: Verify user hasn't already reviewed (prevent race conditions)
        existing_review_check = Review.objects.filter(
            user=request.user,
            pandit=pandit_user
        ).first()
        
        if existing_review_check:
            messages.error(request, 'You have already reviewed this Pandit. You can only submit one review per Pandit.')
            return redirect('reviews:pandit_reviews', pandit_public_id=pandit_user.public_id)
        
        # Get form data
        title = request.POST.get('title', '').strip()
        review_text = request.POST.get('message', '').strip()
        rating = request.POST.get('rating')
        
        # Validation
        if not review_text:
            messages.error(request, 'Review message is required.')
            return render(request, 'module9_reviews/submit_review.html', {
                'pandit': pandit,
                'pandit_user': pandit_user,
                'title': title,
                'message': review_text,
                'rating': rating,
            })
        
        if len(review_text) > 1000:
            messages.error(request, 'Review message must be 1000 characters or less.')
            return render(request, 'module9_reviews/submit_review.html', {
                'pandit': pandit,
                'pandit_user': pandit_user,
                'title': title,
                'message': review_text,
                'rating': rating,
            })
        
        # Parse rating (optional)
        rating_int = None
        if rating:
            try:
                rating_int = int(rating)
                if rating_int < 1 or rating_int > 5:
                    rating_int = None
            except (ValueError, TypeError):
                rating_int = None
        
        # Create review
        try:
            review = ReviewService.create_review(
                reviewer=request.user,
                pandit_id=pandit_user.id,
                rating=rating_int if rating_int else 5,  # Default to 5 if not provided
                review_text=review_text,
                title=title if title else None,
                booking_intent_id=None
            )
            
            messages.success(request, 'Your review has been submitted successfully!')
            # Redirect to reviews page for this pandit
            return redirect('reviews:pandit_reviews', pandit_public_id=pandit_user.public_id)
        
        except ValueError as e:
            # Handle duplicate review error specifically
            if 'already reviewed' in str(e).lower():
                messages.error(request, 'You have already reviewed this Pandit. You can only submit one review per Pandit.')
                return redirect('reviews:pandit_reviews', pandit_public_id=pandit_user.public_id)
            messages.error(request, str(e))
            return render(request, 'module9_reviews/submit_review.html', {
                'pandit': pandit,
                'pandit_user': pandit_user,
                'title': title,
                'message': review_text,
                'rating': rating,
            })
        except Exception as e:
            # Handle database integrity errors (unique constraint violation)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating review: {str(e)}")
            
            # Check if it's a duplicate review error
            if 'unique_user_pandit_review' in str(e) or 'duplicate' in str(e).lower():
                messages.error(request, 'You have already reviewed this Pandit. You can only submit one review per Pandit.')
                return redirect('reviews:pandit_reviews', pandit_public_id=pandit_user.public_id)
            
            messages.error(request, 'An error occurred while submitting your review. Please try again.')
            return render(request, 'module9_reviews/submit_review.html', {
                'pandit': pandit,
                'pandit_user': pandit_user,
                'title': title,
                'message': review_text,
                'rating': rating,
            })
    
    # GET: Show form
    return render(request, 'module9_reviews/submit_review.html', {
        'pandit': pandit,
        'pandit_user': pandit_user,
    })

