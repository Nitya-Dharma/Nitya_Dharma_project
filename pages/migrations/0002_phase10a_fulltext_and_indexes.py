# Phase 10A: Full-text search + read-optimized index (MySQL + all backends)
from django.db import migrations, models


def add_fulltext_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "CREATE FULLTEXT INDEX page_search_idx ON pages_page (title, description)"
        )


def remove_fulltext_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'mysql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE pages_page DROP INDEX page_search_idx"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='page',
            index=models.Index(fields=['city'], name='pages_page_city_id_idx'),
        ),
        migrations.RunPython(add_fulltext_index, remove_fulltext_index, elidable=True),
    ]
