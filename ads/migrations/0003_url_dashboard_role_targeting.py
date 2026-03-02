# Generated for ad engine upgrade: URL exclusion, dashboard, role targeting

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ads', '0002_add_image_and_responsive'),
    ]

    operations = [
        migrations.AddField(
            model_name='advertisement',
            name='exclude_urls',
            field=models.TextField(
                blank=True,
                null=True,
                help_text="Enter URL prefixes (one per line) where this ad should NOT appear. Example: /login/ , /register/",
            ),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='show_on_dashboard',
            field=models.BooleanField(
                default=False,
                help_text="Enable if this ad should appear inside dashboard pages.",
            ),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='target_roles',
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="Optional. Limit ad visibility to specific roles. Example: ['user', 'pandit']",
            ),
        ),
        migrations.AlterField(
            model_name='advertisement',
            name='placement',
            field=models.CharField(
                choices=[
                    ('top', 'Top Banner'),
                    ('sidebar', 'Sidebar'),
                    ('footer', 'Footer'),
                    ('in_content', 'In Content'),
                    ('dashboard_top', 'Dashboard Top'),
                    ('dashboard_sidebar', 'Dashboard Sidebar'),
                ],
                max_length=50,
            ),
        ),
    ]
