# Generated migration to add followers_count and PageRole model

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def add_followers_count_column(apps, schema_editor):
    """Add followers_count column directly via SQL to avoid table remake."""
    from django.db import connection
    cursor = connection.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(pages_page)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'followers_count' not in columns:
        cursor.execute("ALTER TABLE pages_page ADD COLUMN followers_count INTEGER NOT NULL DEFAULT 0")
        cursor.execute("CREATE INDEX IF NOT EXISTS pages_page_followers_count_idx ON pages_page(followers_count)")


def create_page_role_table(apps, schema_editor):
    """Create PageRole table directly via SQL."""
    from django.db import connection
    cursor = connection.cursor()
    
    # Check if table already exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='pages_page_role'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE pages_page_role (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id VARCHAR(36) UNIQUE,
                page_id BIGINT NOT NULL REFERENCES pages_page(id) ON DELETE CASCADE,
                pandit_id BIGINT NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
                role VARCHAR(20) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS pages_pagero_page_pa_idx ON pages_page_role(page_id, pandit_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS pages_pagero_role_cr_idx ON pages_page_role(role, created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS pages_pagero_pandit_idx ON pages_page_role(pandit_id, role)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_pandit_page_role ON pages_page_role(page_id, pandit_id)")


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0009_update_pagepost_and_add_review'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Add followers_count via SQL (avoids table remake)
        migrations.RunPython(add_followers_count_column, migrations.RunPython.noop),
        
        # Step 2: Create PageRole table via SQL
        migrations.RunPython(create_page_role_table, migrations.RunPython.noop),
        
        # Step 3: Create PageRole model in Django state (for ORM)
        migrations.CreateModel(
            name='PageRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.CharField(blank=True, db_index=True, editable=False, max_length=36, null=True, unique=True, verbose_name='Public ID')),
                ('role', models.CharField(choices=[('OWNER', 'Owner'), ('MODERATOR', 'Moderator')], db_index=True, max_length=20, verbose_name='Role')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Created At')),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='page_roles', to='pages.page', verbose_name='Page')),
                ('pandit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='page_roles', to=settings.AUTH_USER_MODEL, verbose_name='Pandit')),
            ],
            options={
                'verbose_name': 'Page Role',
                'verbose_name_plural': 'Page Roles',
                'db_table': 'pages_page_role',
                'ordering': ['-created_at'],
            },
        ),
    ]
