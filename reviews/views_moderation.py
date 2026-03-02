"""
Review Moderation Dashboard Views.

Admin-only views for moderating reported reviews.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage
from accounts.utils import is_admin
from .models import Review
from .models_advanced import ReviewReport


@login_required
def moderation_dashboard(request):
    """
    Review moderation dashboard for Admin/Super Admin.
    
    Shows reported reviews and allows moderation actions.
    """
    # Check permission
    if not (is_admin(request.user) or request.user.is_superuser):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('core:home')
    
    # Get filter parameters
    filter_type = request.GET.get('filter', 'reported')  # reported, hidden, all
    search_query = request.GET.get('search', '').strip()
    
    # Base queryset
    if filter_type == 'reported':
        reviews = Review.objects.filter(reported_count__gt=0).order_by('-reported_count', '-created_at')
    elif filter_type == 'hidden':
        reviews = Review.objects.filter(is_hidden=True).order_by('-created_at')
    else:
        reviews = Review.objects.all().order_by('-created_at')
    
    # Search filter
    if search_query:
        reviews = reviews.filter(
            Q(review_text__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(pandit__email__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(reviews, 20)
    page = int(request.GET.get('page', 1))
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Statistics
    stats = {
        'total_reported': Review.objects.filter(reported_count__gt=0).count(),
        'total_hidden': Review.objects.filter(is_hidden=True).count(),
        'total_reviews': Review.objects.count(),
        'pending_reports': ReviewReport.objects.filter(review_action='pending').count(),
    }
    
    context = {
        'reviews': page_obj,
        'pagination': {
            'page': page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        },
        'filter_type': filter_type,
        'search_query': search_query,
        'stats': stats,
    }
    
    return render(request, 'module9_reviews/moderation_dashboard.html', context)


@login_required
def moderate_review(request, review_id):
    """
    Moderate a review (hide/unhide/verify).
    
    POST /admin/reviews/moderate/<review_id>/
    """
    # Check permission
    if not (is_admin(request.user) or request.user.is_superuser):
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('reviews:moderation_dashboard')
    
    try:
        review = Review.objects.get(id=review_id)
    except Review.DoesNotExist:
        messages.error(request, 'Review not found.')
        return redirect('reviews:moderation_dashboard')
    
    action = request.POST.get('action')
    
    if action == 'hide':
        review.is_hidden = True
        review.visibility_state = Review.HIDDEN
        review.save(update_fields=['is_hidden', 'visibility_state', 'updated_at'])
        messages.success(request, 'Review hidden successfully.')
    elif action == 'unhide':
        review.is_hidden = False
        review.visibility_state = Review.VISIBLE
        review.save(update_fields=['is_hidden', 'visibility_state', 'updated_at'])
        messages.success(request, 'Review unhidden successfully.')
    elif action == 'verify':
        review.is_verified = True
        review.save(update_fields=['is_verified', 'updated_at'])
        messages.success(request, 'Review verified successfully.')
    elif action == 'unverify':
        review.is_verified = False
        review.save(update_fields=['is_verified', 'updated_at'])
        messages.success(request, 'Review unverified successfully.')
    else:
        messages.error(request, 'Invalid action.')
    
    return redirect('reviews:moderation_dashboard')













