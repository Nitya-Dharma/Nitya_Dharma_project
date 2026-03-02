# Generated migration to add cover_image field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0002_add_profile_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='panditprofile',
            name='cover_image',
            field=models.ImageField(blank=True, help_text='Cover photo for profile hero section (recommended: 1920x600px, max 5MB)', null=True, upload_to='profiles/cover_images/', verbose_name='Cover Image'),
        ),
    ]












