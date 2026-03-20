from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('profiles', '0006_alter_panditprofile_location_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='panditprofile',
            name='custom_state_name',
            field=models.CharField(
                blank=True,
                help_text='User-submitted state when selecting "Others" (pending master approval)',
                max_length=100,
                null=True,
                verbose_name='Custom State',
            ),
        ),
        migrations.AddField(
            model_name='panditprofile',
            name='custom_city_name',
            field=models.CharField(
                blank=True,
                help_text='User-submitted city when selecting "Others" (pending master approval)',
                max_length=100,
                null=True,
                verbose_name='Custom City',
            ),
        ),
        migrations.AddField(
            model_name='panditprofile',
            name='custom_area_name',
            field=models.CharField(
                blank=True,
                help_text='User-submitted area when selecting "Others" (pending master approval)',
                max_length=100,
                null=True,
                verbose_name='Custom Area',
            ),
        ),
    ]

