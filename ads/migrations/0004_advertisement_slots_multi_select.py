# Multi-slot support: one ad can appear in multiple positions

from django.db import migrations, models


def backfill_slots_from_placement(apps, schema_editor):
    Advertisement = apps.get_model('ads', 'Advertisement')
    for ad in Advertisement.objects.all():
        if not ad.slots and ad.placement:
            ad.slots = [ad.placement]
            ad.save(update_fields=['slots'])


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0003_url_dashboard_role_targeting'),
    ]

    operations = [
        migrations.AddField(
            model_name='advertisement',
            name='slots',
            field=models.JSONField(
                default=list,
                blank=True,
                help_text='Select one or more positions where this ad should appear.',
            ),
        ),
        migrations.RunPython(backfill_slots_from_placement, migrations.RunPython.noop),
    ]
