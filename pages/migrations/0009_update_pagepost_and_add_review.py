# Generated migration to update PagePost model and add PageReview model

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


def create_pagepost_table_if_not_exists(apps, schema_editor):
    """Create PagePost table if it doesn't exist (for fresh installs)."""
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='pages_page_post'
    """)
    if not cursor.fetchone():
        # Table doesn't exist, create it
        cursor.execute("""
            CREATE TABLE pages_page_post (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_type VARCHAR(20) NOT NULL,
                title VARCHAR(255),
                content TEXT NOT NULL,
                event_date DATE,
                event_time TIME,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                page_id BIGINT NOT NULL REFERENCES pages_page(id) ON DELETE CASCADE
            )
        """)
        # Check if indexes exist before creating
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='pages_pagep_page_id_13f5c7_idx'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE INDEX pages_pagep_page_id_13f5c7_idx ON pages_page_post(page_id, created_at DESC)
            """)
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='pages_pagep_post_ty_57dcff_idx'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE INDEX pages_pagep_post_ty_57dcff_idx ON pages_page_post(post_type, created_at DESC)
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0008_add_gallery_hide_field'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Ensure PagePost table exists (for fresh installs) - skip if table exists
        migrations.RunPython(create_pagepost_table_if_not_exists, migrations.RunPython.noop),
        
        # Step 2: Add new fields to PagePost (nullable first, then we'll backfill)
        migrations.AddField(
            model_name='pagepost',
            name='public_id',
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=36, null=True, unique=True, verbose_name='Public ID'),
        ),
        migrations.AddField(
            model_name='pagepost',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                default=None,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='created_page_posts',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created By'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pagepost',
            name='is_pinned',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Is Pinned'),
        ),
        migrations.AddField(
            model_name='pagepost',
            name='pinned_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Pinned At'),
        ),
        migrations.AddField(
            model_name='pagepost',
            name='is_hidden',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Is Hidden'),
        ),
        migrations.AddField(
            model_name='pagepost',
            name='is_deleted',
            field=models.BooleanField(default=False, editable=False, verbose_name='Is Deleted'),
        ),
        migrations.AddField(
            model_name='pagepost',
            name='event_location',
            field=models.CharField(blank=True, max_length=255, verbose_name='Event Location'),
        ),
        migrations.AlterField(
            model_name='pagepost',
            name='post_type',
            field=models.CharField(
                choices=[('ANNOUNCEMENT', 'Announcement'), ('EVENT', 'Event'), ('UPDATE', 'Update')],
                db_index=True,
                max_length=20,
                verbose_name='Post Type'
            ),
        ),
        migrations.AlterField(
            model_name='pagepost',
            name='title',
            field=models.CharField(max_length=255, verbose_name='Title'),
        ),
        migrations.AlterField(
            model_name='pagepost',
            name='event_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Event Date'),
        ),
        migrations.RemoveField(
            model_name='pagepost',
            name='event_time',
        ),
        migrations.AlterModelTable(
            name='pagepost',
            table='pages_page_post',
        ),
        
        # Step 3: Create PageReview model
        migrations.CreateModel(
            name='PageReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.CharField(blank=True, db_index=True, editable=False, max_length=36, null=True, unique=True, verbose_name='Public ID')),
                ('rating', models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name='Rating')),
                ('review_text', models.TextField(verbose_name='Review Text')),
                ('visibility_state', models.CharField(choices=[('visible', 'Visible'), ('hidden', 'Hidden')], db_index=True, default='visible', max_length=20, verbose_name='Visibility State')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='pages.page', verbose_name='Page')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='page_reviews', to=settings.AUTH_USER_MODEL, verbose_name='Reviewer')),
            ],
            options={
                'verbose_name': 'Page Review',
                'verbose_name_plural': 'Page Reviews',
                'db_table': 'pages_page_review',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pagereview',
            index=models.Index(fields=['page', 'visibility_state'], name='pages_pagere_page_id_idx'),
        ),
        migrations.AddIndex(
            model_name='pagereview',
            index=models.Index(fields=['user', 'created_at'], name='pages_pagere_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='pagereview',
            index=models.Index(fields=['visibility_state', 'created_at'], name='pages_pagere_visibil_idx'),
        ),
        migrations.AddConstraint(
            model_name='pagereview',
            constraint=models.UniqueConstraint(fields=['page', 'user'], name='unique_user_page_review'),
        ),
        
        # Step 4: Add indexes to PagePost
        migrations.AddIndex(
            model_name='pagepost',
            index=models.Index(fields=['page', 'is_hidden', '-created_at'], name='pages_pagep_page_hid_idx'),
        ),
        migrations.AddIndex(
            model_name='pagepost',
            index=models.Index(fields=['post_type', 'is_hidden'], name='pages_pagep_post_typ_idx'),
        ),
        migrations.AddIndex(
            model_name='pagepost',
            index=models.Index(fields=['is_pinned', '-pinned_at'], name='pages_pagep_is_pinn_idx'),
        ),
    ]
