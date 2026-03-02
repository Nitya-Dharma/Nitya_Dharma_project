"""
Signals for updating followers_count when PageFollow records are created/deleted.

TASK 29: Followers of a Deactivated Page

This module ensures that:
- followers_count is kept in sync with actual PageFollow records
- Count remains accurate even when page is INVISIBLE
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import PageFollow, Page

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PageFollow)
def update_followers_count_on_follow(sender, instance, created, **kwargs):
    """
    TASK 29: Update followers_count when a PageFollow is created.
    
    Args:
        sender: PageFollow model
        instance: PageFollow instance
        created: True if new record, False if update
    """
    if created:
        # Update followers_count on the page
        page = instance.page
        # Recalculate from actual count (more reliable than incrementing)
        actual_count = PageFollow.objects.filter(page=page).count()
        if page.followers_count != actual_count:
            Page.objects.filter(id=page.id).update(followers_count=actual_count)
            logger.debug(f"TASK 29: Updated followers_count for page {page.id} to {actual_count}")


@receiver(post_delete, sender=PageFollow)
def update_followers_count_on_unfollow(sender, instance, **kwargs):
    """
    TASK 29: Update followers_count when a PageFollow is deleted (unfollow).
    
    Args:
        sender: PageFollow model
        instance: PageFollow instance being deleted
    """
    # Update followers_count on the page
    page = instance.page
    # Recalculate from actual count (more reliable than decrementing)
    actual_count = PageFollow.objects.filter(page=page).count()
    if page.followers_count != actual_count:
        Page.objects.filter(id=page.id).update(followers_count=actual_count)
        logger.debug(f"TASK 29: Updated followers_count for page {page.id} to {actual_count}")







