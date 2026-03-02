# Update existing ReferralPolicy row to allowed tiers [5, 10, 50, 100].
# Does NOT alter any ReferralLink rows.

from django.db import migrations


def update_policy_tiers(apps, schema_editor):
    ReferralPolicy = apps.get_model('referrals', 'ReferralPolicy')
    policy = ReferralPolicy.objects.filter(pk=1).first()
    if policy:
        policy.allowed_max_use_tiers = [5, 10, 50, 100]
        policy.max_allowed_uses = 100
        policy.save(update_fields=['allowed_max_use_tiers', 'max_allowed_uses'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('referrals', '0006_referral_policy'),
    ]

    operations = [
        migrations.RunPython(update_policy_tiers, noop),
    ]
