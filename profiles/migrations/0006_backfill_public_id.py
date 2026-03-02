"""
Data migration to backfill public_id for existing PanditProfile records.
"""

from django.db import migrations
from core.public_id import generate_public_id


def backfill_public_ids(apps, schema_editor):
    """Generate public_id for all existing profiles."""
    PanditProfile = apps.get_model('profiles', 'PanditProfile')
    
    for profile in PanditProfile.objects.filter(public_id__isnull=True):
        profile.public_id = generate_public_id()
        profile.save(update_fields=['public_id'])


def reverse_backfill(apps, schema_editor):
    """Reverse: Set public_id to None."""
    PanditProfile = apps.get_model('profiles', 'PanditProfile')
    PanditProfile.objects.all().update(public_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0005_add_public_id_fields'),
    ]

    operations = [
        migrations.RunPython(backfill_public_ids, reverse_backfill),
    ]






















