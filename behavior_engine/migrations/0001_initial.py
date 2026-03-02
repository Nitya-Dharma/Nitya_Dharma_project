# Generated manually for Behavior Engine (behavior_event_log table).

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BehaviorEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(db_index=True, max_length=120)),
                ('event_type', models.CharField(db_index=True, max_length=80)),
                ('entity_type', models.CharField(blank=True, max_length=80, null=True)),
                ('entity_id', models.CharField(blank=True, max_length=120, null=True)),
                ('page_url', models.TextField()),
                ('page_title', models.TextField()),
                ('referrer', models.TextField(blank=True, null=True)),
                ('device_type', models.CharField(blank=True, max_length=20, null=True)),
                ('browser', models.TextField(blank=True, null=True)),
                ('os', models.CharField(blank=True, max_length=50, null=True)),
                ('screen_resolution', models.CharField(blank=True, max_length=30, null=True)),
                ('metadata', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'behavior_event_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='behaviorevent',
            index=models.Index(fields=['user', 'event_type'], name='behav_ev_user_event_idx'),
        ),
        migrations.AddIndex(
            model_name='behaviorevent',
            index=models.Index(fields=['entity_type', 'entity_id'], name='behav_ev_entity_idx'),
        ),
        migrations.AddIndex(
            model_name='behaviorevent',
            index=models.Index(fields=['created_at'], name='behav_ev_created_idx'),
        ),
    ]
