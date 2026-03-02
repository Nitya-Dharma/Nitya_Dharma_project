# Generated migration for TASK 2 & 4: Email Verification

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta
from core.public_id import generate_public_id


def create_email_verification_token_table(apps, schema_editor):
    """
    Create EmailVerificationToken table directly via SQL.
    TASK 2: Create table (only if it doesn't exist)
    """
    from django.db import connection
    cursor = connection.cursor()
    
    # Check if table already exists
    if connection.vendor == 'sqlite':
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='accounts_email_verification_token'
        """)
    elif connection.vendor == 'postgresql':
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname='public' AND tablename='accounts_email_verification_token'
        """)
    else:
        # For other databases, assume table doesn't exist
        cursor.execute("SELECT 1 WHERE 0=1")
    
    if not cursor.fetchone():
        # Table doesn't exist, create it (but Django CreateModel will handle this)
        pass


def add_email_verified_to_user(apps, schema_editor):
    """
    Add email_verified column to accounts_user table.
    TASK 4: Add field
    """
    from django.db import connection
    cursor = connection.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(accounts_user)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'email_verified' not in columns:
        cursor.execute("ALTER TABLE accounts_user ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        cursor.execute("CREATE INDEX IF NOT EXISTS accounts_user_email_verified_idx ON accounts_user(email_verified)")


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0006_backfill_public_id'),
    ]

    operations = [
        # Step 1: Add email_verified field to User model (use RunPython for SQLite compatibility)
        migrations.RunPython(add_email_verified_to_user, migrations.RunPython.noop),
        
        # Step 2: Create EmailVerificationToken model
        migrations.CreateModel(
            name='EmailVerificationToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.CharField(blank=True, db_index=True, editable=False, max_length=36, null=True, unique=True, verbose_name='Public ID')),
                ('token', models.CharField(db_index=True, editable=False, max_length=64, unique=True, verbose_name='Verification Token')),
                ('expires_at', models.DateTimeField(db_index=True, verbose_name='Expires At')),
                ('is_used', models.BooleanField(db_index=True, default=False, verbose_name='Is Used')),
                ('used_at', models.DateTimeField(blank=True, null=True, verbose_name='Used At')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Created At')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='email_verification_tokens', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Email Verification Token',
                'verbose_name_plural': 'Email Verification Tokens',
                'db_table': 'accounts_email_verification_token',
                'ordering': ['-created_at'],
            },
        ),
        
        # Step 4: Add email_verified field in Django state
        migrations.AddField(
            model_name='user',
            name='email_verified',
            field=models.BooleanField(db_index=True, default=False, verbose_name='Email Verified'),
        ),
    ]
