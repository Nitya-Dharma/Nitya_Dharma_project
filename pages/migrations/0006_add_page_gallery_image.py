# Generated manually to avoid interactive prompts

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pages', '0005_add_page_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='PageGalleryImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('public_id', models.CharField(blank=True, db_index=True, editable=False, max_length=36, null=True, unique=True, verbose_name='Public ID')),
                ('image', models.ImageField(upload_to='pages/gallery/', verbose_name='Image')),
                ('caption', models.CharField(blank=True, max_length=255, verbose_name='Caption')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Created At')),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gallery_images', to='pages.page', verbose_name='Page')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='uploaded_gallery_images', to=settings.AUTH_USER_MODEL, verbose_name='Uploaded By')),
            ],
            options={
                'verbose_name': 'Page Gallery Image',
                'verbose_name_plural': 'Page Gallery Images',
                'db_table': 'pages_page_gallery_image',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pagegalleryimage',
            index=models.Index(fields=['page', 'created_at'], name='pages_page_page_id_created_idx'),
        ),
    ]

