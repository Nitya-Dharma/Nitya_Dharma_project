# STEP-1: Backend Location Infrastructure - add location fields to PanditProfile
# Reversible, MySQL-compatible. Does not modify existing columns.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0003_phase10a_fulltext_search'),
    ]

    operations = [
        migrations.AddField(
            model_name='panditprofile',
            name='latitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text="Latitude coordinate of the pandit's current service location",
                max_digits=9,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='panditprofile',
            name='longitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text="Longitude coordinate of the pandit's current service location",
                max_digits=9,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='panditprofile',
            name='location_source',
            field=models.CharField(
                choices=[('admin', 'Admin'), ('gps', 'GPS'), ('manual', 'Manual')],
                default='manual',
                help_text='Indicates how the location was set',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='panditprofile',
            name='location_updated_at',
            field=models.DateTimeField(
                auto_now=True,
                help_text='Timestamp when the location was last updated',
            ),
        ),
        migrations.AddField(
            model_name='panditprofile',
            name='is_location_verified',
            field=models.BooleanField(
                default=False,
                help_text='Indicates whether the location has been verified',
            ),
        ),
        migrations.AddIndex(
            model_name='panditprofile',
            index=models.Index(fields=['latitude'], name='profile_latitude_idx'),
        ),
        migrations.AddIndex(
            model_name='panditprofile',
            index=models.Index(fields=['longitude'], name='profile_longitude_idx'),
        ),
    ]
