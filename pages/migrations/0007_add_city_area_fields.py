# Generated migration to add city and area FK fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0001_initial'),  # Adjust if needed
        ('pages', '0006_add_page_gallery_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='city',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pages',
                to='masterdata.city',
                verbose_name='City'
            ),
        ),
        migrations.AddField(
            model_name='page',
            name='area',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pages',
                to='masterdata.localarea',
                verbose_name='Area'
            ),
        ),
    ]



















