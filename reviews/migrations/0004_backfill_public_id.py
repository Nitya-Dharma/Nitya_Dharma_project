"""
Data migration to backfill public_id for existing Review records.
"""

from django.db import migrations
from core.public_id import generate_public_id


def backfill_public_ids(apps, schema_editor):
    """Generate public_id for all existing reviews."""
    Review = apps.get_model('reviews', 'Review')
    
    for review in Review.objects.filter(public_id__isnull=True):
        review.public_id = generate_public_id()
        review.save(update_fields=['public_id'])


def reverse_backfill(apps, schema_editor):
    """Reverse: Set public_id to None."""
    Review = apps.get_model('reviews', 'Review')
    Review.objects.all().update(public_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0003_add_public_id_field'),
    ]

    operations = [
        migrations.RunPython(backfill_public_ids, reverse_backfill),
    ]






















