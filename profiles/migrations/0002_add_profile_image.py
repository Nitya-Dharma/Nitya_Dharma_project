# Generated manually to add profile_image field to PanditProfile

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0006_backfill_public_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='panditprofile',
            name='profile_image',
            field=models.ImageField(
                blank=True,
                help_text='Profile picture for the Pandit (recommended: square image, max 5MB)',
                null=True,
                upload_to='profiles/pandit_images/',
                verbose_name='Profile Image'
            ),
        ),
    ]

