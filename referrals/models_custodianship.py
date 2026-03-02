"""
Referral Custodianship model for preserving trust chain integrity.

When a Pandit who has referred others is deactivated, this model tracks
who manages the referral chain (custodian) while preserving the original
referrer identity for historical accuracy.
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.public_id import generate_public_id

User = get_user_model()


class ReferralCustodian(models.Model):
    """
    Tracks custodianship of referral chains when original referrer is deactivated.
    
    Key Principles:
    - Original referrer identity is NEVER modified
    - Custodian manages the chain but does NOT replace history
    - Used only when referrer is deactivated
    - Super Admin is always the custodian
    """
    
    # Public ID for external references
    public_id = models.CharField(
        max_length=36,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        editable=False,
        verbose_name='Public ID',
        help_text='Public-facing UUIDv7 identifier'
    )
    
    # Original referrer (the Pandit who referred others, now deactivated)
    # This is NEVER modified - preserves historical truth
    original_referrer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Never delete referral history
        related_name='custodianships',
        verbose_name='Original Referrer',
        help_text='The Pandit who originally referred others (now deactivated). This is immutable.'
    )
    
    # Custodian (always Super Admin)
    # Manages the referral chain but does NOT replace the referrer in history
    custodian = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='managed_custodianships',
        verbose_name='Custodian',
        help_text='Super Admin who manages this referral chain. Does not replace original referrer in history.'
    )
    
    # Reason for custodianship assignment
    reason = models.TextField(
        verbose_name='Reason',
        help_text='Reason for assigning custodianship (e.g., "Referrer deactivated", "Account suspended")'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At',
        help_text='When custodianship was assigned'
    )
    
    # Status constants (defined before Meta class)
    STATUS_ACTIVE = 'active'
    STATUS_RELEASED = 'released'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_RELEASED, 'Released'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        verbose_name='Status',
        help_text='Custodianship status'
    )
    
    class Meta:
        verbose_name = 'Referral Custodian'
        verbose_name_plural = 'Referral Custodians'
        db_table = 'referrals_referral_custodian'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['original_referrer', 'status']),
            models.Index(fields=['custodian', 'status']),
            models.Index(fields=['status']),
        ]
        # One active custodianship per referrer
        constraints = [
            models.UniqueConstraint(
                fields=['original_referrer'],
                condition=models.Q(status='active'),
                name='unique_active_custodianship_per_referrer'
            )
        ]
    
    def __str__(self):
        return f"Custodianship for {self.original_referrer.email} (managed by {self.custodian.email})"
    
    def save(self, *args, **kwargs):
        """Auto-generate public_id if missing."""
        if not self.public_id:
            self.public_id = generate_public_id()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_custodian_for_referrer(cls, referrer):
        """
        Get active custodian for a given referrer.
        
        Returns:
            ReferralCustodian instance or None
        """
        return cls.objects.filter(
            original_referrer=referrer,
            status=cls.STATUS_ACTIVE
        ).first()
    
    @classmethod
    def assign_custodianship(cls, referrer, custodian, reason):
        """
        Assign custodianship for a referrer.
        
        Args:
            referrer: User instance (the deactivated Pandit)
            custodian: User instance (Super Admin)
            reason: str (reason for assignment)
        
        Returns:
            ReferralCustodian instance
        """
        # Deactivate any existing custodianships
        cls.objects.filter(
            original_referrer=referrer,
            status=cls.STATUS_ACTIVE
        ).update(status=cls.STATUS_RELEASED)
        
        # Create new custodianship
        return cls.objects.create(
            original_referrer=referrer,
            custodian=custodian,
            reason=reason,
            status=cls.STATUS_ACTIVE
        )

