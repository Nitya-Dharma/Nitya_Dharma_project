"""
Core mixins for Nitya Dharma platform.

This module provides reusable mixins for common functionality across models.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class SoftDeletableMixin(models.Model):
    """
    Mixin that prevents hard deletion of model instances.
    
    Instead of deleting, instances are soft-deactivated using:
    - is_active (bool): Whether the instance is active
    - is_visible (bool): Whether the instance is visible to end users
    - deactivated_at (datetime): When the instance was deactivated
    - deactivation_reason (text): Reason for deactivation
    
    Rules:
    - Hard DELETE operations are blocked
    - delete() raises ValidationError
    - Use deactivate() method for soft deletion
    - All historical data remains queryable
    """
    
    # Soft deletion fields
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Is Active',
        help_text='Whether this instance is active. False means soft-deactivated.'
    )
    
    is_visible = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name='Is Visible',
        help_text='Whether this instance is visible to end users. False means hidden from public view.'
    )
    
    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Deactivated At',
        help_text='Timestamp when this instance was soft-deactivated'
    )
    
    deactivation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='Deactivation Reason',
        help_text='Reason for deactivation (for audit purposes)'
    )
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to prevent hard deletion.
        
        Raises:
            ValidationError: Always raises, as hard deletion is not allowed.
        """
        from core.audit import log_blocked_deletion
        
        model_name = self.__class__.__name__
        entity_id = getattr(self, 'pk', 'unknown')
        
        # Log the blocked deletion attempt
        log_blocked_deletion(self, actor=None, reason="Hard deletion blocked - use deactivate() instead")
        
        logger.warning(
            f"BLOCKED: Attempted hard deletion of {model_name} (ID: {entity_id}). "
            f"Hard deletion is not allowed. Use deactivate() instead."
        )
        raise ValidationError(
            f"Hard deletion is not allowed for {model_name}. "
            f"Use deactivate() method for soft deactivation instead."
        )
    
    def deactivate(self, reason=None, actor=None):
        """
        Soft-deactivate this instance.
        
        Args:
            reason (str, optional): Reason for deactivation
            actor (User, optional): User performing the deactivation (for audit)
        
        Returns:
            bool: True if deactivation was successful
        """
        if not self.is_active:
            logger.info(f"{self.__class__.__name__} (ID: {self.pk}) is already deactivated.")
            return True
        
        self.is_active = False
        self.is_visible = False
        self.deactivated_at = timezone.now()
        if reason:
            self.deactivation_reason = reason
        
        try:
            self.save(update_fields=['is_active', 'is_visible', 'deactivated_at', 'deactivation_reason'])
            
            # Log audit entry
            self._log_deactivation(actor, reason)
            
            logger.info(
                f"Soft-deactivated {self.__class__.__name__} (ID: {self.pk}) "
                f"by {actor.email if actor else 'system'}. Reason: {reason or 'Not provided'}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error deactivating {self.__class__.__name__} (ID: {self.pk}): {e}",
                exc_info=True
            )
            return False
    
    def reactivate(self, reason=None, actor=None):
        """
        Reactivate a soft-deactivated instance.
        
        Args:
            reason (str, optional): Reason for reactivation
            actor (User, optional): User performing the reactivation (for audit)
        
        Returns:
            bool: True if reactivation was successful
        """
        if self.is_active:
            logger.info(f"{self.__class__.__name__} (ID: {self.pk}) is already active.")
            return True
        
        self.is_active = True
        self.is_visible = True
        self.deactivated_at = None
        self.deactivation_reason = None
        
        try:
            self.save(update_fields=['is_active', 'is_visible', 'deactivated_at', 'deactivation_reason'])
            
            # Log audit entry
            self._log_reactivation(actor, reason)
            
            logger.info(
                f"Reactivated {self.__class__.__name__} (ID: {self.pk}) "
                f"by {actor.email if actor else 'system'}. Reason: {reason or 'Not provided'}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Error reactivating {self.__class__.__name__} (ID: {self.pk}): {e}",
                exc_info=True
            )
            return False
    
    def _log_deactivation(self, actor=None, reason=None):
        """
        Log deactivation event for audit purposes.
        
        This method can be overridden by subclasses to use their own audit logging.
        """
        from core.audit import log_deactivation
        log_deactivation(self, actor=actor, reason=reason)
    
    def _log_reactivation(self, actor=None, reason=None):
        """
        Log reactivation event for audit purposes.
        
        This method can be overridden by subclasses to use their own audit logging.
        """
        from core.audit import log_reactivation
        log_reactivation(self, actor=actor, reason=reason)

