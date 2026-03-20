# Add combined (latitude, longitude) index for location-based search performance.
# MySQL compatible. Does not alter existing columns or indexes.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0004_add_location_fields_step1'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='panditprofile',
            index=models.Index(fields=['latitude', 'longitude'], name='profile_lat_lon_idx'),
        ),
    ]
