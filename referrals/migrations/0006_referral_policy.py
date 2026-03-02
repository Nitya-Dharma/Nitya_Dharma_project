# Referral Policy - tier-based dynamic defaults. Existing referral links untouched.

import django.core.validators
from django.db import migrations, models


def create_default_policy(apps, schema_editor):
    ReferralPolicy = apps.get_model('referrals', 'ReferralPolicy')
    ReferralPolicy.objects.get_or_create(
        pk=1,
        defaults={
            'default_expiry_days': 30,
            'allowed_max_use_tiers': [5],
            'max_allowed_expiry_days': 90,
            'max_allowed_uses': 100,
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0005_referralcustodian_alter_referrallink_status_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferralPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('default_expiry_days', models.PositiveIntegerField(default=30, help_text='Default validity in days for new referral links when not overridden.', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(365)], verbose_name='Default Expiry (Days)')),
                ('allowed_max_use_tiers', models.JSONField(default=list, help_text='List of allowed max_uses values (e.g. [3, 5, 10]). Admin Pandits select from these.', verbose_name='Allowed Max Use Tiers')),
                ('max_allowed_expiry_days', models.PositiveIntegerField(default=90, help_text='Maximum expiry days an Admin Pandit can select for a new link.', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(365)], verbose_name='Max Allowed Expiry (Days)')),
                ('max_allowed_uses', models.PositiveIntegerField(default=100, help_text='Upper cap for max_uses (validates against ReferralLink validator).', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(100)], verbose_name='Max Allowed Uses (Cap)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Referral Policy',
                'verbose_name_plural': 'Referral Policies',
                'db_table': 'referrals_referral_policy',
            },
        ),
        migrations.RunPython(create_default_policy, migrations.RunPython.noop),
    ]
