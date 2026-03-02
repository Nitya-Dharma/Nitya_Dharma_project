# Generated migration for TASK 1: Email Verification Resend Capability

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_add_email_verification'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='email_verified_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Email Verified At'),
        ),
        migrations.AddField(
            model_name='user',
            name='last_verification_email_sent_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Last Verification Email Sent At'),
        ),
    ]













