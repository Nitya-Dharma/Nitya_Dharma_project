"""
Signals for Profiles app.

Automatically creates PanditProfile when a User with role='pandit' is created.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_pandit_profile(sender, instance, created, **kwargs):
    """
    Automatically create PanditProfile when a User with role='pandit' is created.
    
    This ensures that every Pandit user has a profile immediately after registration,
    making dashboard links and profile management work seamlessly.
    
    Args:
        sender: The User model class
        instance: The User instance that was saved
        created: Boolean indicating if this is a new record
    """
    # Only create profile for new Pandit users
    if not created:
        return
    
    # Only create profile if user has pandit role
    if instance.role != 'pandit':
        return
    
    # Check if profile already exists (avoid duplicates)
    if hasattr(instance, 'pandit_profile'):
        logger.debug(f"PanditProfile already exists for {instance.email}")
        return
    
    try:
        from .models import PanditProfile
        
        # 🔒 SAFE: Check if profile exists first to avoid unnecessary save() calls
        profile = PanditProfile.objects.filter(user=instance).first()
        if not profile:
            # Create new profile
            profile = PanditProfile(user=instance)
            # Save immediately to get primary key (required before any M2M access)
            profile.save()
            logger.info(f"✅ PanditProfile created automatically for {instance.email} (User ID: {instance.id})")
        else:
            logger.debug(f"PanditProfile already exists for {instance.email} (User ID: {instance.id})")
    except Exception as e:
        # Log error but don't raise - profile can be created manually later if needed
        logger.error(
            f"❌ Failed to create PanditProfile for {instance.email} (User ID: {instance.id}): {str(e)}",
            exc_info=True
        )

