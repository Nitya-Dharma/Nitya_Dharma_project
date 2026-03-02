"""
Review services.

Tasks:
- 9.3: Review Submission Eligibility & Validation
- 9.4: Review Visibility & Access Rules
- 9.5: Review Editing & Deletion Constraints
- 9.6: Ratings Aggregation & Display Inputs
- 9.9: Review Reporting Rules
- 9.10: Review Moderation Outcomes & Visibility States
- 9.11: Governance & Appeals Integration
- 9.12: Analytics Event Emission
- 9.13: Notification Triggers

Business logic for review operations.
All operations are social proof only - no ranking, trust, or search influence.
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Review

User = get_user_model()
logger = logging.getLogger(__name__)


class ReviewService:
    """
    Service for review operations.
    
    All operations are social proof only.
    No ranking, trust, or search influence.
    """
    
    @staticmethod
    @transaction.atomic
    def create_review(
        reviewer,
        pandit_id,
        rating,
        review_text,
        title=None,
        booking_intent_id=None
    ):
        """
        Create a new review.
        
        Task 9.3: Review Submission Eligibility & Validation
        
        Args:
            reviewer: User object (reviewer)
            pandit_id: ID of Pandit user
            rating: Integer rating (1-5)
            review_text: Review text content
            booking_intent_id: Optional Booking Intent ID (for context)
        
        Returns:
            Review object
        
        Raises:
            ValueError: If validation fails
        
        Note:
            - Logged-in users ONLY can create
            - One review per user per pandit
            - No spam scoring
            - No ML
            - Emits analytics event (Task 9.12)
            - Emits notification event (Task 9.13)
        """
        # Validate reviewer
        if not reviewer or not reviewer.is_authenticated:
            raise ValueError('Reviewer must be authenticated')
        
        if reviewer.status != 'active':
            raise ValueError('Reviewer must have active status')
        
        # Get and validate pandit
        try:
            pandit = User.objects.get(id=pandit_id, role='pandit', status='active', is_active=True)
        except User.DoesNotExist:
            raise ValueError('Pandit not found or not eligible')
        
        # Ensure reviewer and pandit are different
        if reviewer.id == pandit.id:
            raise ValueError('Reviewer and Pandit must be different users')
        
        # Validate rating
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            raise ValueError('Rating must be an integer between 1 and 5')
        
        # Validate review text
        if not review_text or not review_text.strip():
            raise ValueError('Review text cannot be empty')
        
        # Check for existing review (one review per user per pandit)
        # This check prevents duplicate reviews at the application level
        existing_review = Review.objects.filter(user=reviewer, pandit=pandit).first()
        if existing_review:
            raise ValueError('You have already reviewed this Pandit. You can only submit one review per Pandit.')
        
        # Create review with audit snapshots
        review = Review.objects.create(
            user=reviewer,
            pandit=pandit,
            rating=rating,
            title=title.strip() if title else None,
            review_text=review_text.strip(),
            visibility_state=Review.VISIBLE,
            # Audit snapshots
            reviewer_status_at_creation=reviewer.status,
            pandit_status_at_creation=pandit.status,
        )
        
        # Task 9.12: Emit analytics event
        ReviewService._emit_review_created_event(review)
        
        # Task 9.13: Emit notification event
        ReviewService._emit_review_created_notification(review)
        
        logger.info(f"Review {review.id} created: {reviewer.email} → {pandit.email} (rating: {rating})")
        
        return review
    
    @staticmethod
    def get_visible_reviews_for_pandit(pandit_id, limit=None):
        """
        Get visible reviews for a Pandit.
        
        Task 9.4: Review Visibility & Access Rules
        
        Args:
            pandit_id: ID of Pandit user
            limit: Optional limit on number of reviews
        
        Returns:
            QuerySet of Review objects
        
        Note:
            - Only visible reviews
            - No hidden or under_review reviews
            - No ranking or sorting beyond default
        """
        queryset = Review.objects.filter(
            pandit_id=pandit_id,
            visibility_state=Review.VISIBLE
        ).select_related('user', 'pandit').order_by('-created_at')
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @staticmethod
    def get_reviews_by_reviewer(reviewer, visibility_state=None):
        """
        Get reviews created by a reviewer.
        
        Task 9.4: Review Visibility & Access Rules
        
        Args:
            reviewer: User object
            visibility_state: Optional visibility state filter
        
        Returns:
            QuerySet of Review objects
        """
        queryset = Review.objects.filter(user=reviewer)
        
        if visibility_state:
            queryset = queryset.filter(visibility_state=visibility_state)
        
        return queryset.select_related('user', 'pandit').order_by('-created_at')
    
    @staticmethod
    def get_all_reviews_for_governance(visibility_state=None):
        """
        Get all reviews for governance review.
        
        Task 9.11: Governance & Appeals Integration
        
        Args:
            visibility_state: Optional visibility state filter
        
        Returns:
            QuerySet of Review objects
        
        Note:
            - Admin-only visibility
            - Includes all visibility states
        """
        queryset = Review.objects.all()
        
        if visibility_state:
            queryset = queryset.filter(visibility_state=visibility_state)
        
        return queryset.select_related('user', 'pandit').order_by('-created_at')
    
    @staticmethod
    def change_visibility_state(review_id, new_state, admin_user, reason=None):
        """
        Change review visibility state (governance only).
        
        Task 9.10: Review Moderation Outcomes & Visibility States
        
        Args:
            review_id: ID of Review
            new_state: New visibility state (visible/hidden/under_review)
            admin_user: Admin user performing the action
            reason: Optional reason for state change
        
        Returns:
            Review object (updated)
        
        Raises:
            ValueError: If validation fails
            PermissionError: If user is not admin
        
        Note:
            - Only admins can change visibility
            - No auto-removal
            - Manual moderation only
        """
        # Verify admin user
        if not admin_user or admin_user.role != 'admin':
            raise PermissionError('Only admins can change review visibility')
        
        # Validate state
        if new_state not in dict(Review.VISIBILITY_STATE_CHOICES):
            raise ValueError(f'Invalid visibility state: {new_state}')
        
        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            raise ValueError('Review not found')
        
        # Update visibility state
        review.visibility_state = new_state
        review.last_visibility_change_at = timezone.now()
        review.save(update_fields=['visibility_state', 'last_visibility_change_at', 'updated_at'])
        
        # Task 9.12: Emit analytics event
        ReviewService._emit_review_visibility_changed_event(review, new_state, reason)
        
        # Task 9.13: Emit notification event
        ReviewService._emit_review_visibility_changed_notification(review, new_state)
        
        logger.info(f"Review {review.id} visibility changed to {new_state} by admin {admin_user.email}")
        
        return review
    
    @staticmethod
    def get_rating_aggregation_for_pandit(pandit_id):
        """
        Get rating aggregation for a Pandit (display-only).
        
        Task 9.6: Ratings Aggregation & Display Inputs
        
        Args:
            pandit_id: ID of Pandit user
        
        Returns:
            dict: {
                'average_rating': float,
                'total_reviews': int,
                'rating_distribution': dict (1-5 counts)
            }
        
        Note:
            - Simple aggregation only
            - No weighting
            - No comparisons
            - Display-only input for Module 10
            - No ranking meaning
        """
        reviews = Review.objects.filter(
            pandit_id=pandit_id,
            visibility_state=Review.VISIBLE
        )
        
        total_reviews = reviews.count()
        
        if total_reviews == 0:
            return {
                'average_rating': 0.0,
                'total_reviews': 0,
                'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        # Calculate average
        total_rating = sum(review.rating for review in reviews)
        average_rating = round(total_rating / total_reviews, 2)
        
        # Calculate distribution
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for review in reviews:
            rating_distribution[review.rating] = rating_distribution.get(review.rating, 0) + 1
        
        return {
            'average_rating': average_rating,
            'total_reviews': total_reviews,
            'rating_distribution': rating_distribution
        }
    
    @staticmethod
    def _emit_review_created_event(review):
        """
        Emit analytics event for review creation.
        
        Task 9.12: Analytics Event Emission
        
        Args:
            review: Review object
        
        Note:
            - No PII
            - Backend-only emission
            - No analytics decisions
        """
        # TODO: When Module 14 (Analytics) is implemented, emit event here
        # Event structure:
        # {
        #     'type': 'review.created',
        #     'review_id': review.id,
        #     'pandit_id': review.pandit_id,
        #     'rating': review.rating,
        #     'timestamp': timezone.now().isoformat()
        # }
        
        logger.info(f"Event: review.created (review_id={review.id})")
    
    @staticmethod
    def _emit_review_visibility_changed_event(review, new_state, reason=None):
        """
        Emit analytics event for visibility change.
        
        Task 9.12: Analytics Event Emission
        
        Args:
            review: Review object
            new_state: New visibility state
            reason: Optional reason
        """
        # TODO: When Module 14 (Analytics) is implemented, emit event here
        logger.info(f"Event: review.visibility_changed (review_id={review.id}, state={new_state})")
    
    @staticmethod
    def _emit_review_created_notification(review):
        """
        Emit notification event for review creation.
        
        Task 9.13: Notification Triggers
        
        Args:
            review: Review object
        
        Note:
            - Trigger events only
            - Delivery via Module 17
            - No notification logic here
        """
        # TODO: When Module 17 (Notifications) is implemented, emit event here
        # Event structure:
        # {
        #     'type': 'review.created',
        #     'review_id': review.id,
        #     'pandit_id': review.pandit_id,
        #     'reviewer_id': review.user_id,
        #     'timestamp': timezone.now().isoformat()
        # }
        
        logger.info(f"Notification event: review.created (review_id={review.id})")
    
    @staticmethod
    def _emit_review_visibility_changed_notification(review, new_state):
        """
        Emit notification event for visibility change.
        
        Task 9.13: Notification Triggers
        
        Args:
            review: Review object
            new_state: New visibility state
        """
        # TODO: When Module 17 (Notifications) is implemented, emit event here
        logger.info(f"Notification event: review.visibility_changed (review_id={review.id}, state={new_state})")
    
    @staticmethod
    @transaction.atomic
    def report_review(review_id, reporter, reason):
        """
        Report a review for abuse.
        
        Task 9.9: Review Reporting Rules
        
        Args:
            review_id: ID of Review
            reporter: User object (user or pandit reporting)
            reason: Reason for reporting
        
        Returns:
            Review object (updated)
        
        Raises:
            ValueError: If validation fails
        
        Note:
            - Users and Pandits may report reviews
            - Reporting ≠ deletion
            - Governance decides outcome (Module 11)
        """
        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            raise ValueError('Review not found')
        
        # Validate reporter
        if not reporter or not reporter.is_authenticated:
            raise ValueError('Reporter must be authenticated')
        
        # Validate reason
        if not reason or not reason.strip():
            raise ValueError('Reason is required')
        
        # Report the review
        review.is_reported = True
        review.reported_at = timezone.now()
        review.reported_reason = reason.strip()
        review.save(update_fields=['is_reported', 'reported_at', 'reported_reason', 'updated_at'])
        
        # Task 9.12: Emit analytics event
        ReviewService._emit_review_reported_event(review, reporter)
        
        # Task 9.13: Emit notification event
        ReviewService._emit_review_reported_notification(review, reporter)
        
        logger.info(f"Review {review.id} reported by {reporter.email}: {reason[:50]}")
        
        return review
    
    @staticmethod
    def _emit_review_reported_event(review, reporter):
        """
        Emit analytics event for review reporting.
        
        Task 9.12: Analytics Event Emission
        
        Args:
            review: Review object
            reporter: User object who reported
        """
        # TODO: When Module 14 (Analytics) is implemented, emit event here
        logger.info(f"Event: review.reported (review_id={review.id}, reporter_id={reporter.id})")
    
    @staticmethod
    def _emit_review_reported_notification(review, reporter):
        """
        Emit notification event for review reporting.
        
        Task 9.13: Notification Triggers
        
        Args:
            review: Review object
            reporter: User object who reported
        """
        # TODO: When Module 17 (Notifications) is implemented, emit event here
        logger.info(f"Notification event: review.reported (review_id={review.id})")
    
    @staticmethod
    def can_edit_review(user, review):
        """
        Check if user can edit a review.
        
        Task 9.5: Review Editing & Deletion Constraints
        
        Args:
            user: User object
            review: Review object
        
        Returns:
            bool: True if user can edit review
        
        Rules:
            - Reviews are immutable after moderation
            - Optional edit window (time-bounded, if implemented)
            - Pandits can NEVER edit reviews
        """
        if not user or not user.is_authenticated:
            return False
        
        # Only reviewer can edit their own review
        if review.user_id != user.id:
            return False
        
        # Cannot edit if visibility has been changed by governance
        if review.last_visibility_change_at is not None:
            return False
        
        # Optional: Time-bounded edit window (e.g., 24 hours)
        # For now, reviews are immutable after creation
        # This can be implemented later if needed
        
        return False  # Reviews are immutable after creation
    
    @staticmethod
    def can_delete_review(user, review):
        """
        Check if user can delete a review.
        
        Task 9.5: Review Editing & Deletion Constraints
        
        Args:
            user: User object
            review: Review object
        
        Returns:
            bool: True if user can delete review
        
        Rules:
            - Pandits can NEVER delete reviews
            - Use soft-delete / visibility flags only
            - Only governance can hide/remove
        """
        # Pandits can NEVER delete reviews
        # Only governance can change visibility
        return False

