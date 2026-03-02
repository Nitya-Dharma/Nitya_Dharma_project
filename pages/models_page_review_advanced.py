"""
Advanced Page Review System Models.

Additional models for helpful voting and detailed reporting for temple/page reviews.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import PageReview


class PageReviewHelpfulVote(models.Model):
    """
    Tracks which users found a page review helpful.
    
    Prevents duplicate votes from the same user for the same review.
    """
    review = models.ForeignKey(
        PageReview,
        on_delete=models.CASCADE,
        related_name='helpful_votes',
        verbose_name='Review',
        help_text='The review that was voted as helpful'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='page_review_helpful_votes',
        verbose_name='User',
        help_text='The user who marked this review as helpful'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='Timestamp when this vote was created'
    )
    
    class Meta:
        verbose_name = 'Page Review Helpful Vote'
        verbose_name_plural = 'Page Review Helpful Votes'
        db_table = 'pages_pagereviewhelpfulvote'
        unique_together = [['review', 'user']]
        indexes = [
            models.Index(fields=['review', 'user']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} found page review {self.review.id} helpful"
    
    def clean(self):
        """Validate that user cannot vote on their own review."""
        if self.review and self.user and self.review.user_id == self.user_id:
            raise ValidationError('You cannot vote on your own review.')
    
    def save(self, *args, **kwargs):
        """Override save to validate and update helpful_count."""
        self.full_clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update helpful_count on review
        if is_new:
            PageReview.objects.filter(id=self.review_id).update(
                helpful_count=models.F('helpful_count') + 1
            )


class PageReviewReport(models.Model):
    """
    Detailed report tracking for page reviews.
    
    Tracks individual reports with reasons and timestamps.
    """
    # Report reason choices
    SPAM = 'spam'
    INAPPROPRIATE = 'inappropriate'
    FAKE = 'fake'
    OFFENSIVE = 'offensive'
    OTHER = 'other'
    
    REASON_CHOICES = [
        (SPAM, 'Spam'),
        (INAPPROPRIATE, 'Inappropriate Content'),
        (FAKE, 'Fake Review'),
        (OFFENSIVE, 'Offensive Language'),
        (OTHER, 'Other'),
    ]
    
    review = models.ForeignKey(
        PageReview,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='Review',
        help_text='The review being reported'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='page_review_reports',
        verbose_name='Reporter',
        help_text='The user who reported this review'
    )
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        default=OTHER,
        verbose_name='Reason',
        help_text='Reason for reporting this review'
    )
    reason_text = models.TextField(
        blank=True,
        null=True,
        verbose_name='Reason Details',
        help_text='Additional details about why this review was reported'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='Timestamp when this report was created'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reviewed_page_reports',
        null=True,
        blank=True,
        verbose_name='Reviewed By',
        help_text='Admin who reviewed this report'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Reviewed At',
        help_text='Timestamp when this report was reviewed'
    )
    review_action = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('dismissed', 'Dismissed'),
            ('hidden', 'Review Hidden'),
        ],
        default='pending',
        verbose_name='Review Action',
        help_text='Action taken on this report'
    )
    
    class Meta:
        verbose_name = 'Page Review Report'
        verbose_name_plural = 'Page Review Reports'
        db_table = 'pages_pagereviewreport'
        unique_together = [['review', 'user']]  # One report per user per review
        indexes = [
            models.Index(fields=['review', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['review_action', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report on page review {self.review.id} by {self.user.email} - {self.reason}"
    
    def clean(self):
        """Validate that user cannot report their own review."""
        if self.review and self.user and self.review.user_id == self.user_id:
            raise ValidationError('You cannot report your own review.')
    
    def save(self, *args, **kwargs):
        """Override save to update reported_count on review."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update reported_count on review
        if is_new:
            PageReview.objects.filter(id=self.review_id).update(
                reported_count=models.F('reported_count') + 1
            )
            
            # Auto-hide if reported_count exceeds threshold
            review = PageReview.objects.get(id=self.review_id)
            if review.reported_count >= 5:
                review.is_hidden = True
                review.visibility_state = PageReview.HIDDEN
                review.save(update_fields=['is_hidden', 'visibility_state'])













