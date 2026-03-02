"""
Signals for tracking configuration audit logging.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import TrackingConfiguration, TrackingConfigurationAudit
import json

User = get_user_model()


@receiver(pre_save, sender=TrackingConfiguration)
def track_configuration_changes(sender, instance, **kwargs):
    """Store old values before save for audit logging."""
    if instance.pk:
        try:
            old_instance = TrackingConfiguration.objects.get(pk=instance.pk)
            instance._old_values = {
                'provider_type': old_instance.provider_type,
                'is_active': old_instance.is_active,
                'head_snippet': old_instance.head_snippet,
                'body_snippet': old_instance.body_snippet,
                'footer_snippet': old_instance.footer_snippet,
                'excluded_route_patterns': old_instance.excluded_route_patterns,
            }
        except TrackingConfiguration.DoesNotExist:
            instance._old_values = None
    else:
        instance._old_values = None


@receiver(post_save, sender=TrackingConfiguration)
def create_audit_log(sender, instance, created, **kwargs):
    """Create audit log entry for tracking configuration changes."""
    if not instance.updated_by:
        return
    
    action = 'created' if created else 'updated'
    
    # Determine if status changed
    if not created and instance._old_values:
        if instance._old_values.get('is_active') != instance.is_active:
            if instance.is_active:
                action = 'enabled'
            else:
                action = 'disabled'
    
    # Prepare old and new values
    old_value = None
    new_value = None
    
    if created:
        new_value = {
            'provider_type': instance.provider_type,
            'is_active': instance.is_active,
            'head_snippet': instance.head_snippet[:100] + '...' if instance.head_snippet and len(instance.head_snippet) > 100 else instance.head_snippet,
            'body_snippet': instance.body_snippet[:100] + '...' if instance.body_snippet and len(instance.body_snippet) > 100 else instance.body_snippet,
            'footer_snippet': instance.footer_snippet[:100] + '...' if instance.footer_snippet and len(instance.footer_snippet) > 100 else instance.footer_snippet,
            'excluded_route_patterns': instance.excluded_route_patterns,
        }
    else:
        if instance._old_values:
            old_value = {
                'provider_type': instance._old_values.get('provider_type'),
                'is_active': instance._old_values.get('is_active'),
                'head_snippet': instance._old_values.get('head_snippet', '')[:100] + '...' if instance._old_values.get('head_snippet') and len(instance._old_values.get('head_snippet', '')) > 100 else instance._old_values.get('head_snippet'),
                'body_snippet': instance._old_values.get('body_snippet', '')[:100] + '...' if instance._old_values.get('body_snippet') and len(instance._old_values.get('body_snippet', '')) > 100 else instance._old_values.get('body_snippet'),
                'footer_snippet': instance._old_values.get('footer_snippet', '')[:100] + '...' if instance._old_values.get('footer_snippet') and len(instance._old_values.get('footer_snippet', '')) > 100 else instance._old_values.get('footer_snippet'),
                'excluded_route_patterns': instance._old_values.get('excluded_route_patterns'),
            }
        
        new_value = {
            'provider_type': instance.provider_type,
            'is_active': instance.is_active,
            'head_snippet': instance.head_snippet[:100] + '...' if instance.head_snippet and len(instance.head_snippet) > 100 else instance.head_snippet,
            'body_snippet': instance.body_snippet[:100] + '...' if instance.body_snippet and len(instance.body_snippet) > 100 else instance.body_snippet,
            'footer_snippet': instance.footer_snippet[:100] + '...' if instance.footer_snippet and len(instance.footer_snippet) > 100 else instance.footer_snippet,
            'excluded_route_patterns': instance.excluded_route_patterns,
        }
    
    # Create audit log
    TrackingConfigurationAudit.objects.create(
        tracking_configuration=instance,
        changed_by=instance.updated_by,
        action=action,
        old_value=json.dumps(old_value) if old_value else None,
        new_value=json.dumps(new_value) if new_value else None,
    )


