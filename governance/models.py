"""
Governance data models for Nitya Dharma platform.

Task 11.4: Governance Case Model & State Machine
Task 11.9: Appeal models
Task 11.11: Audit models

This module defines models for governance cases, actions, appeals, and audit logs.
All governance actions are human-controlled and auditable.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class GovernanceCase(models.Model):
    """
    Represents a governance case (report, review, or action).
    
    Task 11.4: Governance Case Model & State Machine
    
    A case tracks the lifecycle of a governance action from creation
    through review, resolution, and potential appeal.
    
    States:
    - open: Case is open and awaiting review
    - under_review: Case is being reviewed by governance
    - resolved: Case has been resolved (action taken or dismissed)
    - appealed: Case resolution has been appealed
    """
    
    STATE_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('appealed', 'Appealed'),
    ]
    
    CASE_TYPE_CHOICES = [
        ('pandit_report', 'Pandit Report'),
        ('media_report', 'Media Report'),
        ('review_report', 'Review Report'),
        ('manual_review', 'Manual Review'),
    ]
    
    # Case identification
    case_type = models.CharField(
        max_length=50,
        choices=CASE_TYPE_CHOICES,
        verbose_name='Case Type',
        help_text='Type of governance case'
    )
    
    # Subject: The Pandit or entity being reviewed
    subject_pandit = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='governance_cases',
        verbose_name='Subject Pandit',
        help_text='The Pandit this case is about',
        limit_choices_to={'role': 'pandit'}
    )
    
    # Reporter: Who created the case (if applicable)
    reporter = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='reported_cases',
        null=True,
        blank=True,
        verbose_name='Reporter',
        help_text='User who reported this case (if applicable)'
    )
    
    # Case state
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default='open',
        db_index=True,
        verbose_name='State',
        help_text='Current state of the governance case'
    )
    
    # Case details
    reason = models.TextField(
        verbose_name='Reason',
        help_text='Reason for the case (report reason, review reason, etc.)'
    )
    
    # Review assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='assigned_governance_cases',
        null=True,
        blank=True,
        verbose_name='Assigned To',
        help_text='Governance role assigned to review this case',
        limit_choices_to={'role__in': ['admin']}
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='When the case was created'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At',
        help_text='When the case was last updated'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Resolved At',
        help_text='When the case was resolved'
    )
    
    # Immutable audit fields (snapshots at creation)
    reporter_status_at_creation = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Reporter Status at Creation',
        help_text='Immutable snapshot of reporter status when case was created'
    )
    subject_status_at_creation = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Subject Status at Creation',
        help_text='Immutable snapshot of subject Pandit status when case was created'
    )
    
    class Meta:
        verbose_name = 'Governance Case'
        verbose_name_plural = 'Governance Cases'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['state', 'created_at']),
            models.Index(fields=['subject_pandit', 'state']),
            models.Index(fields=['case_type', 'state']),
        ]
    
    def __str__(self):
        return f"Case {self.id}: {self.get_case_type_display()} - {self.subject_pandit.email} ({self.get_state_display()})"
    
    def can_transition_to(self, new_state):
        """
        Check if case can transition to new state.
        
        Task 11.4: State machine validation
        
        Valid transitions:
        - open -> under_review
        - under_review -> resolved
        - resolved -> appealed
        - appealed -> under_review (re-review after appeal)
        """
        valid_transitions = {
            'open': ['under_review'],
            'under_review': ['resolved'],
            'resolved': ['appealed'],
            'appealed': ['under_review', 'resolved'],
        }
        return new_state in valid_transitions.get(self.state, [])


class GovernanceAction(models.Model):
    """
    Represents a governance action taken on a case.
    
    Task 11.5: Governance Action Execution Logic
    
    Actions are immutable records of what governance did.
    All actions are human-triggered and auditable.
    """
    
    ACTION_TYPE_CHOICES = [
        ('limited_block', 'Limited Block'),
        ('full_block', 'Full Block'),
        ('visibility_restriction', 'Visibility Restriction'),
        ('dismissed', 'Dismissed'),
        ('no_action', 'No Action'),
    ]
    
    # Related case
    case = models.ForeignKey(
        GovernanceCase,
        on_delete=models.PROTECT,
        related_name='actions',
        verbose_name='Case',
        help_text='The governance case this action belongs to'
    )
    
    # Action details
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPE_CHOICES,
        verbose_name='Action Type',
        help_text='Type of governance action taken'
    )
    
    # Actor: Who performed the action
    performed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='governance_actions',
        verbose_name='Performed By',
        help_text='Governance role who performed this action',
        limit_choices_to={'role__in': ['admin']}
    )
    
    # Action details
    reason = models.TextField(
        verbose_name='Reason',
        help_text='Reason for this action'
    )
    
    # Timestamp
    performed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Performed At',
        help_text='When this action was performed'
    )
    
    # Immutable audit fields
    performer_role_at_action = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Performer Role at Action',
        help_text='Immutable snapshot of performer role when action was taken'
    )
    subject_status_at_action = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Subject Status at Action',
        help_text='Immutable snapshot of subject status when action was taken'
    )
    
    class Meta:
        verbose_name = 'Governance Action'
        verbose_name_plural = 'Governance Actions'
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['case', 'performed_at']),
            models.Index(fields=['action_type', 'performed_at']),
        ]
    
    def __str__(self):
        return f"Action {self.id}: {self.get_action_type_display()} on Case {self.case.id} by {self.performed_by.email}"


class PartialBlock(models.Model):
    """
    Partial block model for Admin Pandit actions.
    
    Tracks reversible partial blocks on Pandits:
    - Disable booking intents
    - Hide from search
    - Disable reviews
    - Temporarily unlist profile
    
    All blocks are reversible and logged for audit.
    """
    
    RESTRICTION_TYPE_CHOICES = [
        ('booking_intent_block', 'Disable Booking Intents'),
        ('search_visibility_block', 'Hide from Search'),
        ('review_block', 'Disable Reviews'),
        ('profile_unlist', 'Temporarily Unlist Profile'),
    ]
    
    # Blocked Pandit
    pandit = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='partial_blocks',
        verbose_name='Pandit',
        help_text='The Pandit being partially blocked',
        limit_choices_to={'role': 'pandit'}
    )
    
    # Restriction type
    restriction_type = models.CharField(
        max_length=50,
        choices=RESTRICTION_TYPE_CHOICES,
        verbose_name='Restriction Type',
        help_text='Type of partial restriction applied'
    )
    
    # Block details
    reason = models.TextField(
        verbose_name='Reason',
        help_text='Reason for the partial block'
    )
    
    # Applied by
    applied_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='applied_partial_blocks',
        verbose_name='Applied By',
        help_text='Admin Pandit who applied this block',
        limit_choices_to={'role': 'admin'}
    )
    
    # Block state
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active',
        help_text='Whether this block is currently active'
    )
    
    # Timestamps
    applied_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Applied At',
        help_text='When the block was applied'
    )
    removed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Removed At',
        help_text='When the block was removed (if removed)'
    )
    removed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='removed_partial_blocks',
        null=True,
        blank=True,
        verbose_name='Removed By',
        help_text='Admin Pandit who removed this block',
        limit_choices_to={'role': 'admin'}
    )
    
    class Meta:
        verbose_name = 'Partial Block'
        verbose_name_plural = 'Partial Blocks'
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['pandit', 'is_active']),
            models.Index(fields=['restriction_type', 'is_active']),
            models.Index(fields=['applied_at']),
        ]
    
    def __str__(self):
        status = 'Active' if self.is_active else 'Removed'
        return f"{self.get_restriction_type_display()} on {self.pandit.email} ({status})"
