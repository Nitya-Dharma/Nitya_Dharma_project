"""
Data migration to backfill public_id for existing User records.

This migration preserves all existing primary key values and generates
UUIDv7 public_ids for all existing users.
"""

from django.db import migrations
from core.public_id import generate_public_id


def backfill_public_ids(apps, schema_editor):
    """Generate public_id for all existing users."""
    User = apps.get_model('accounts', 'User')
    
    for user in User.objects.filter(public_id__isnull=True):
        user.public_id = generate_public_id()
        user.save(update_fields=['public_id'])


def reverse_backfill(apps, schema_editor):
    """Reverse: Set public_id to None (but keep field)."""
    User = apps.get_model('accounts', 'User')
    User.objects.all().update(public_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_add_public_id_fields'),
    ]

    operations = [
        migrations.RunPython(backfill_public_ids, reverse_backfill),
    ]






















