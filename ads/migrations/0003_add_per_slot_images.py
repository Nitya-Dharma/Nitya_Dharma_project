# Per-slot image fields for position-specific uploads (backward compatible)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0002_alter_advertisement_image_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='advertisement',
            name='image_top',
            field=models.ImageField(blank=True, null=True, upload_to='ads/banners/'),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='image_sidebar',
            field=models.ImageField(blank=True, null=True, upload_to='ads/banners/'),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='image_footer',
            field=models.ImageField(blank=True, null=True, upload_to='ads/banners/'),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='image_in_content',
            field=models.ImageField(blank=True, null=True, upload_to='ads/banners/'),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='image_dashboard_top',
            field=models.ImageField(blank=True, null=True, upload_to='ads/banners/'),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='image_dashboard_sidebar',
            field=models.ImageField(blank=True, null=True, upload_to='ads/banners/'),
        ),
    ]
