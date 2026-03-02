# Generated migration to add is_hidden and is_deleted fields to PageGalleryImage

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0007_add_city_area_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagegalleryimage',
            name='is_hidden',
            field=models.BooleanField(default=False, db_index=True, verbose_name='Is Hidden'),
        ),
        migrations.AddField(
            model_name='pagegalleryimage',
            name='is_deleted',
            field=models.BooleanField(default=False, editable=False, verbose_name='Is Deleted'),
        ),
    ]


