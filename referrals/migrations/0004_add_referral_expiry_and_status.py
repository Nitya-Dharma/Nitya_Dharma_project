# Generated migration for TASK 1: Referral Model with Expiry

from django.db import migrations, models
from django.utils import timezone
from datetime import timedelta


def set_default_expiry_for_existing_referrals(apps, schema_editor):
    """
    Set default expiry (30 days from now) for existing referrals with null expires_at.
    TASK 1: Handle existing data
    """
    ReferralLink = apps.get_model('referrals', 'ReferralLink')
    default_expiry = timezone.now() + timedelta(days=30)
    
    ReferralLink.objects.filter(expires_at__isnull=True).update(expires_at=default_expiry)


def add_status_and_make_expires_at_required(apps, schema_editor):
    """
    Add status field and make expires_at required.
    TASK 1: Migration operations
    """
    from django.db import connection
    
    cursor = connection.cursor()
    
    # Add status field (temporary, nullable first)
    try:
        cursor.execute("ALTER TABLE referrals_referral_link ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
    except Exception:
        pass  # Column might already exist
    
    # Update existing records to have status='active'
    cursor.execute("UPDATE referrals_referral_link SET status='active' WHERE status IS NULL")
    
    # Add indexes
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS referrals_referr_status_idx ON referrals_referral_link(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS referrals_referr_expires_idx ON referrals_referral_link(expires_at)")
    except Exception:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0003_add_public_id_fields'),
    ]

    operations = [
        # Step 1: Set default expiry for existing referrals
        migrations.RunPython(set_default_expiry_for_existing_referrals, migrations.RunPython.noop),
        
        # Step 2: Add status field (nullable initially)
        migrations.AddField(
            model_name='referrallink',
            name='status',
            field=models.CharField(
                choices=[('active', 'Active'), ('expired', 'Expired'), ('revoked', 'Revoked')],
                db_index=True,
                default='active',
                max_length=20,
                verbose_name='Status'
            ),
        ),
        
        # Step 3: Make expires_at required (after setting defaults)
        migrations.AlterField(
            model_name='referrallink',
            name='expires_at',
            field=models.DateTimeField(
                db_index=True,
                help_text='Expiry date for this referral link (required). Referral auto-expires when expires_at < now()',
                verbose_name='Expires At'
            ),
        ),
        
        # Step 4: Add indexes via RunPython (for SQLite compatibility)
        migrations.RunPython(add_status_and_make_expires_at_required, migrations.RunPython.noop),
    ]
