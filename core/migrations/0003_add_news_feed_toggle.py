# Data migration: create default news_feed feature toggle (disabled)

from django.db import migrations


def create_news_feed_toggle(apps, schema_editor):
    FeatureToggle = apps.get_model('core', 'FeatureToggle')
    if not FeatureToggle.objects.filter(name='news_feed').exists():
        FeatureToggle.objects.create(
            name='news_feed',
            enabled=False,
            description='Personalized news feed at /feed/. When disabled, feed is hidden and endpoints return 404.',
        )


def remove_news_feed_toggle(apps, schema_editor):
    FeatureToggle = apps.get_model('core', 'FeatureToggle')
    FeatureToggle.objects.filter(name='news_feed').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_featuretoggle'),
    ]

    operations = [
        migrations.RunPython(create_news_feed_toggle, remove_news_feed_toggle),
    ]
