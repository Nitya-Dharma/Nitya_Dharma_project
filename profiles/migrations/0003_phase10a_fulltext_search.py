# Phase 10A: Full-text search index for Pandit search (MySQL only)
from django.db import migrations


def add_fulltext_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "CREATE FULLTEXT INDEX pandit_search_idx ON profiles_panditprofile (display_name, about_description)"
        )


def remove_fulltext_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE profiles_panditprofile DROP INDEX pandit_search_idx"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0002_phase81_performance_indexes'),
    ]

    operations = [
        migrations.RunPython(add_fulltext_index, remove_fulltext_index, elidable=True),
    ]
