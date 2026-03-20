# Generated manually for feature toggle (admin-controlled news feed visibility)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeatureToggle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=255, unique=True)),
                ('enabled', models.BooleanField(default=False)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Feature Toggle',
                'verbose_name_plural': 'Feature Toggles',
                'db_table': 'core_featuretoggle',
                'ordering': ['name'],
            },
        ),
    ]
