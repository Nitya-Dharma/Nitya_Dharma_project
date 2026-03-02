# Generated manually to fix slug field and add new fields
# Using raw SQL to handle SQLite limitations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0004_update_page_core_models'),
    ]

    operations = [
        # Step 1: Add new fields first (these are simple additions)
        migrations.AddField(
            model_name='page',
            name='address',
            field=models.TextField(
                null=True,
                blank=True,
                verbose_name='Address',
                help_text='Temple/Page address'
            ),
        ),
        migrations.AddField(
            model_name='page',
            name='cover_image',
            field=models.ImageField(
                upload_to='pages/covers/',
                null=True,
                blank=True,
                verbose_name='Cover Image',
                help_text='Cover image for the page'
            ),
        ),
        migrations.AddField(
            model_name='page',
            name='profile_image',
            field=models.ImageField(
                upload_to='pages/profiles/',
                null=True,
                blank=True,
                verbose_name='Profile Image',
                help_text='Profile image for the page'
            ),
        ),
        
        # Step 2: Make slug nullable (this will trigger table remake, but new fields are already added)
        migrations.AlterField(
            model_name='page',
            name='slug',
            field=models.SlugField(
                max_length=255,
                null=True,
                blank=True,
                db_index=True,
                verbose_name='Slug',
                help_text='URL-friendly identifier (auto-generated from title if empty, unique per page_type)'
            ),
        ),
        
        # Step 3: Change title to TextField (this will also trigger table remake)
        migrations.AlterField(
            model_name='page',
            name='title',
            field=models.TextField(
                verbose_name='Title',
                help_text='Page title (no length limit)'
            ),
        ),
        
        # Step 4: Remove unique_together
        migrations.AlterUniqueTogether(
            name='page',
            unique_together=set(),
        ),
    ]
