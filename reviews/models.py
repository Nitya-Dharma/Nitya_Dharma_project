from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from core.public_id import generate_public_id
from core.audit import log_blocked_deletion


class Review(models.Model):
    """
    Review model for user-submitted feedback about Pandits.
    
    Represents user-submitted, post-interaction feedback.
    Reviews are opinion-based, subjective, and immutable once submitted.
    
    Ownership:
    - One User → Many Reviews (as author)
    - One Pandit → Many Reviews (as subject)
    - Review belongs to User (author), Pandit is subject only
    
    This model is:
    - Booking-agnostic
    - Payment-agnostic
    - Trust-agnostic
    - Search-agnostic
    - Ranking-agnostic
    - Safe for future extensions
    
    NOTE:
    - Role enforcement (user must be logged-in, pandit must have role='pandit') 
      is handled at service/permission layer, not DB level
    - Content immutability is enforced at service layer, not in model save()
    - No audit model or audit storage is implemented here; audit is deferred to Task 9.13
    - clean() method is for Django admin/forms only, not runtime enforcement
    """
    
    # VISIBILITY_STATE_CHOICES
    VISIBLE = 'visible'
    UNDER_REVIEW = 'under_review'
    HIDDEN = 'hidden'
    
    VISIBILITY_STATE_CHOICES = [
        (VISIBLE, 'Visible'),
        (UNDER_REVIEW, 'Under Review'),
        (HIDDEN, 'Hidden'),
    ]
    
    # CREATED_SOURCE_CHOICES
    WEB = 'web'
    APP = 'app'
    
    CREATED_SOURCE_CHOICES = [
        (WEB, 'Web'),
        (APP, 'App'),
    ]
    
    # Public ID: UUIDv7 for external-facing URLs/APIs
    # Internal ID (id) remains BIGINT for performance (joins, indexes)
    # Security: Never expose internal BIGINT IDs in URLs, templates, or APIs
    public_id = models.CharField(
        max_length=36,  # UUID format length
        unique=True,
        db_index=True,
        null=True,  # Nullable initially for existing records
        blank=True,
        editable=False,  # Auto-generated, never manually set
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier for URLs and APIs. Internal ID (id) is used for database joins.'
    )
    
    # Core Identity Fields
    # review_id is auto-generated as primary key (id)
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='Timestamp when this review was submitted'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='Timestamp when this review was last updated'
    )
    
    # Author Context (Immutable)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_authored',
        verbose_name='Review Author',
        help_text='The logged-in user who authored this review. NOTE: Role enforcement (user must be logged-in) is handled at service/permission layer, not at database level. No anonymous reviews allowed.'
    )
    
    # Subject Reference
    pandit = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_received',
        verbose_name='Reviewed Pandit',
        help_text='The Pandit who is the subject of this review. NOTE: Role enforcement (pandit must have role="pandit") is handled at service/permission layer, not at database level. This is a reference only, no authority implied.'
    )
    
    # Review Content (Immutable)
    title = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='Review Title',
        help_text='Short title for the review (optional but recommended)'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True,
        verbose_name='Rating',
        help_text='User-submitted rating (1-5 scale). Optional, display-only. Content is immutable after submission.'
    )
    review_text = models.TextField(
        max_length=1000,
        verbose_name='Review Message',
        help_text='User-submitted review content. Content is immutable after submission.'
    )
    
    # Visibility State (Non-Behavioral)
    visibility_state = models.CharField(
        max_length=20,
        choices=VISIBILITY_STATE_CHOICES,
        default=VISIBLE,
        verbose_name='Visibility State',
        help_text='Current visibility state of the review. Visibility ≠ moderation outcome. Only governance can change this state.'
    )
    
    # System Metadata (Non-Interpretive)
    created_source = models.CharField(
        max_length=10,
        choices=CREATED_SOURCE_CHOICES,
        default=WEB,
        verbose_name='Created Source',
        help_text='Source platform where review was submitted (web or app)'
    )
    last_visibility_change_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Visibility Change At',
        help_text='Timestamp when visibility state was last changed by governance. Null if never changed.'
    )
    
    # Immutable Audit Fields (Task 9.2)
    # These fields capture state at creation time for audit purposes
    reviewer_status_at_creation = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Reviewer Status at Creation',
        help_text='Snapshot of reviewer status when review was created (for audit)'
    )
    pandit_status_at_creation = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Pandit Status at Creation',
        help_text='Snapshot of pandit status when review was created (for audit)'
    )
    
    # Reporting Fields (Task 9.9)
    is_reported = models.BooleanField(
        default=False,
        verbose_name='Is Reported',
        help_text='Whether this review has been reported for abuse'
    )
    reported_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Reported At',
        help_text='Timestamp when review was reported'
    )
    reported_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='Reported Reason',
        help_text='Reason for reporting (user/pandit provided)'
    )
    
    # Advanced Review System Fields
    helpful_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Helpful Count',
        help_text='Number of users who found this review helpful'
    )
    reported_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Reported Count',
        help_text='Number of times this review has been reported'
    )
    is_hidden = models.BooleanField(
        default=False,
        verbose_name='Is Hidden',
        help_text='Whether this review is hidden from public view due to moderation'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Is Verified',
        help_text='Whether this review is verified (e.g., from completed booking)'
    )
    
    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        db_table = 'reviews_review'
        ordering = ['-created_at']  # Newest first
        indexes = [
            models.Index(fields=['pandit', 'visibility_state']),
            models.Index(fields=['user', 'visibility_state']),
            models.Index(fields=['visibility_state', 'created_at']),
            models.Index(fields=['pandit', 'created_at']),
        ]
        # Prevent duplicate reviews: one user can review one pandit only once
        # NOTE: This constraint is conceptual; actual enforcement happens at service layer
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'pandit'],
                name='unique_user_pandit_review',
                # NOTE: This constraint prevents duplicate reviews at DB level,
                # but business logic enforcement (e.g., one review per interaction)
                # is handled at service layer (Task 9.5)
            ),
        ]
    
    def __str__(self):
        """String representation of review."""
        user_name = self.user.get_full_name() or self.user.email
        pandit_name = self.pandit.get_full_name() or self.pandit.email
        return f"Review by {user_name} for {pandit_name} ({self.rating}/5) - {self.visibility_state}"
    
    def clean(self):
        """
        Validation logic for Django admin and forms.
        
        NOTE: This is NOT enforcement logic. Actual validation enforcement
        happens at the service/permission layer (Task 9.5 and beyond).
        This method is provided for Django admin and form validation only.
        
        Ensures:
        - Rating is within valid range (1-5)
        - Review text is not empty
        - User and Pandit are different (user cannot review themselves)
        """
        from django.core.exceptions import ValidationError
        
        # Validate rating range (already enforced by validators, but explicit here)
        if self.rating < 1 or self.rating > 5:
            raise ValidationError({
                'rating': 'Rating must be between 1 and 5.'
            })
        
        # Validate review text is not empty
        if not self.review_text or not self.review_text.strip():
            raise ValidationError({
                'review_text': 'Review text cannot be empty.'
            })
        
        # Validate user and pandit are different
        if self.user_id and self.pandit_id and self.user_id == self.pandit_id:
            raise ValidationError({
                'pandit': 'User cannot review themselves.'
            })
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        Reviews must never be hard-deleted. Use visibility_state='hidden' for hiding.
        """
        log_blocked_deletion(self, actor=None, reason="Review hard deletion blocked - use visibility_state='hidden' instead")
        raise ValidationError(
            f"Hard deletion is not allowed for Review. "
            f"Use visibility_state='hidden' to hide the review from public view."
        )
    
    # NOTE: No save() override. Content immutability and validation enforcement 
    # happen at service layer (Task 9.5+). clean() is provided for Django admin/forms only, 
    # not for runtime enforcement.
