# Phase 10A: Full-text search index for review content (MySQL only)
from django.db import migrations


def add_fulltext_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "CREATE FULLTEXT INDEX review_search_idx ON reviews_review (title, review_text)"
        )


def remove_fulltext_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE reviews_review DROP INDEX review_search_idx"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_fulltext_index, remove_fulltext_index, elidable=True),
    ]
