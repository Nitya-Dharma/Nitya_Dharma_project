"""
Global Deletion Guard — System-Level Safety Net

PART 4 — AUTOMATED GUARDRAILS

This module provides:
- Model-level deletion protection
- Central deletion policy registry
- Automatic enforcement of "no hard delete" rule

RULE (ABSOLUTE):
If an entity has EVER been referenced, logged, reviewed, booked, followed, approved, or linked
→ it must NEVER be hard-deleted.

Allowed actions only:
- Deactivate
- Hide
- Transfer custodianship
- Anonymize display
- Preserve audit
"""

from django.core.exceptions import ValidationError
from django.db import models
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# CENTRAL DELETION POLICY REGISTRY (TASK 4.2)
# ============================================================================

DELETION_POLICY = {
    # User & Identity
    "User": "NO_DELETE",
    "PanditProfile": "NO_DELETE",
    
    # Pages & Content
    "TemplePage": "NO_DELETE",
    "BrandPage": "NO_DELETE",
    "ServicePage": "NO_DELETE",
    "PagePost": "NO_DELETE",
    "PageReview": "NO_DELETE",
    
    # Bookings & Intents
    "BookingIntent": "NO_DELETE",
    
    # Trust & Referrals
    "Referral": "NO_DELETE",
    
    # Engagement
    "EngagementEvent": "NO_DELETE",
    "PageFollower": "NO_DELETE",
    
    # Notifications
    "Notification": "NO_DELETE",
    
    # Audit & History
    "AuditLog": "IMMUTABLE",
    
    # Master Data (already protected in models, but listed for completeness)
    "City": "NO_DELETE",
    "Mandal": "NO_DELETE",
    "LocalArea": "NO_DELETE",
    "PoojaCategory": "NO_DELETE",
    "Pooja": "NO_DELETE",
    "Language": "NO_DELETE",
    "CountryCode": "NO_DELETE",
    "ProfileCompletionRule": "NO_DELETE",
    "UploadConfig": "NO_DELETE",
}

POLICY_NO_DELETE = "NO_DELETE"
POLICY_IMMUTABLE = "IMMUTABLE"
POLICY_ALLOW_DELETE = "ALLOW_DELETE"  # For non-historical entities only


def get_deletion_policy(model_class):
    """
    Get deletion policy for a model class.
    
    Args:
        model_class: Django model class or model name string
    
    Returns:
        str: Policy string (NO_DELETE, IMMUTABLE, ALLOW_DELETE)
    """
    if isinstance(model_class, str):
        model_name = model_class
    else:
        model_name = model_class.__name__
    
    return DELETION_POLICY.get(model_name, POLICY_ALLOW_DELETE)


def is_deletion_protected(model_class):
    """
    Check if a model is protected from deletion.
    
    Args:
        model_class: Django model class or model name string
    
    Returns:
        bool: True if deletion is protected
    """
    policy = get_deletion_policy(model_class)
    return policy in (POLICY_NO_DELETE, POLICY_IMMUTABLE)


# ============================================================================
# DELETION GUARD MIXIN (TASK 4.1)
# ============================================================================

class DeletionGuardMixin:
    """
    Mixin that prevents hard deletion of protected models.
    
    Usage:
        class MyModel(DeletionGuardMixin, models.Model):
            ...
    
    Behavior:
        - Overrides delete() to check deletion policy
        - Raises ProtectedError if deletion is not allowed
        - Logs audit event: DELETE_ATTEMPT_BLOCKED
        - Suggests deactivation instead
    """
    
    def delete(self, using=None, keep_parents=False):
        """
        Override delete() to enforce deletion policy.
        
        Raises:
            ValidationError: If deletion is not allowed
        
        Returns:
            None (never returns normally)
        """
        model_name = self.__class__.__name__
        policy = get_deletion_policy(model_name)
        
        if policy in (POLICY_NO_DELETE, POLICY_IMMUTABLE):
            # Log the attempt
            from core.audit import log_blocked_deletion
            log_blocked_deletion(
                self,
                actor=None,  # Will be set by caller if available
                reason=f"Hard deletion blocked by deletion policy: {policy}"
            )
            
            # Determine appropriate error message
            if policy == POLICY_IMMUTABLE:
                error_msg = (
                    f"Hard deletion is not allowed for {model_name} '{self}'. "
                    f"This entity is IMMUTABLE and must never be deleted. "
                    f"Historical data must be preserved."
                )
            else:
                error_msg = (
                    f"Hard deletion is not allowed for {model_name} '{self}'. "
                    f"This entity has historical references and must be deactivated instead. "
                    f"Use the 'deactivate()' method or set status to INACTIVE/INVISIBLE."
                )
            
            logger.warning(
                f"DELETE_ATTEMPT_BLOCKED: {model_name} (id={self.pk}) - {error_msg}",
                extra={
                    'model': model_name,
                    'instance_id': self.pk,
                    'policy': policy,
                }
            )
            
            raise ValidationError(error_msg)
        
        # If deletion is allowed, proceed with normal deletion
        super().delete(using=using, keep_parents=keep_parents)
    
    def deactivate(self, reason=None, actor=None):
        """
        Deactivate this instance (soft delete).
        
        This method should be overridden by models that implement soft deletion.
        Default implementation sets status to INACTIVE if status field exists.
        
        Args:
            reason: Optional reason for deactivation
            actor: Optional User who performed the action
        
        Returns:
            self: For method chaining
        """
        # Check if model has status field
        if hasattr(self, 'status'):
            if hasattr(self, 'STATUS_INACTIVE'):
                self.status = self.STATUS_INACTIVE
            elif hasattr(self, 'STATUS_DEACTIVATED'):
                self.status = self.STATUS_DEACTIVATED
            else:
                # Try common status values
                if hasattr(self, 'STATUS_CHOICES'):
                    # Find inactive status from choices
                    for choice_value, choice_label in self.STATUS_CHOICES:
                        if 'inactive' in choice_value.lower() or 'deactivated' in choice_value.lower():
                            self.status = choice_value
                            break
            
            # Also set is_active if it exists
            if hasattr(self, 'is_active'):
                self.is_active = False
            
            # Save the changes
            update_fields = ['status', 'updated_at']
            if hasattr(self, 'is_active'):
                update_fields.append('is_active')
            
            self.save(update_fields=update_fields)
            
            # Log audit event
            from core.audit import log_deactivation
            log_deactivation(
                self,
                actor=actor,
                reason=reason or f"{self.__class__.__name__} deactivated"
            )
        
        return self


# ============================================================================
# QUERYSET DELETE PROTECTION (TASK 4.1)
# ============================================================================

class ProtectedQuerySet(models.QuerySet):
    """
    QuerySet that prevents bulk deletion of protected models.
    
    Usage:
        class MyModelManager(models.Manager):
            def get_queryset(self):
                return ProtectedQuerySet(self.model, using=self._db)
    """
    
    def delete(self):
        """
        Override bulk delete() to check deletion policy.
        
        Raises:
            ValidationError: If any instance in queryset is protected
        """
        model_name = self.model.__name__
        policy = get_deletion_policy(model_name)
        
        if policy in (POLICY_NO_DELETE, POLICY_IMMUTABLE):
            count = self.count()
            
            # Log the attempt
            logger.warning(
                f"BULK_DELETE_ATTEMPT_BLOCKED: {model_name} (count={count}) - "
                f"Bulk deletion blocked by deletion policy: {policy}",
                extra={
                    'model': model_name,
                    'count': count,
                    'policy': policy,
                }
            )
            
            raise ValidationError(
                f"Bulk deletion is not allowed for {model_name}. "
                f"This model is protected by deletion policy: {policy}. "
                f"Use deactivation instead of bulk delete."
            )
        
        # If deletion is allowed, proceed with normal deletion
        return super().delete()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_deletion_allowed(model_class, instance=None):
    """
    Check if deletion is allowed for a model or instance.
    
    Args:
        model_class: Django model class or model name string
        instance: Optional model instance
    
    Returns:
        tuple: (is_allowed: bool, reason: str)
    """
    policy = get_deletion_policy(model_class)
    
    if policy in (POLICY_NO_DELETE, POLICY_IMMUTABLE):
        return False, f"Deletion blocked by policy: {policy}"
    
    return True, "Deletion allowed"


def enforce_deletion_policy(model_class):
    """
    Decorator/helper to enforce deletion policy on a model class.
    
    This can be used to automatically apply DeletionGuardMixin to models
    that are in the DELETION_POLICY registry.
    """
    policy = get_deletion_policy(model_class)
    
    if policy in (POLICY_NO_DELETE, POLICY_IMMUTABLE):
        # Check if model already has DeletionGuardMixin
        if not issubclass(model_class, DeletionGuardMixin):
            # Apply mixin (this would require model class modification)
            # For now, models should explicitly inherit DeletionGuardMixin
            pass
    
    return model_class

