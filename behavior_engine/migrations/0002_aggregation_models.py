# Behavior Intelligence aggregation models (read-only snapshots; raw events unchanged).

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('behavior_engine', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserInterestProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('interest_score', models.FloatField(default=0.0)),
                ('category_affinity', models.JSONField(default=dict)),
                ('geo_preference', models.JSONField(default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='behavior_interest_profiles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'behavior_user_interest_profile',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='TrendingSnapshotDaily',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('entity_type', models.CharField(db_index=True, max_length=80)),
                ('entity_id', models.CharField(db_index=True, max_length=120)),
                ('trending_score', models.FloatField(default=0.0)),
                ('recency_decay_index', models.FloatField(default=1.0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'behavior_trending_snapshot_daily',
                'ordering': ['-date', '-trending_score'],
            },
        ),
        migrations.CreateModel(
            name='EntityPopularitySnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('entity_type', models.CharField(db_index=True, max_length=80)),
                ('entity_id', models.CharField(db_index=True, max_length=120)),
                ('view_count', models.PositiveIntegerField(default=0)),
                ('click_count', models.PositiveIntegerField(default=0)),
                ('engagement_score', models.FloatField(default=0.0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'behavior_entity_popularity_snapshot',
                'ordering': ['-date', '-engagement_score'],
            },
        ),
        migrations.CreateModel(
            name='UserSessionMetrics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(db_index=True, max_length=120)),
                ('date', models.DateField(db_index=True)),
                ('event_count', models.PositiveIntegerField(default=0)),
                ('duration_seconds', models.PositiveIntegerField(blank=True, null=True)),
                ('scroll_depth_max', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('page_views', models.PositiveIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'behavior_user_session_metrics',
                'ordering': ['-date', '-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='FeedImpressionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(db_index=True, max_length=120)),
                ('entity_type', models.CharField(blank=True, max_length=80, null=True)),
                ('entity_id', models.CharField(blank=True, max_length=120, null=True)),
                ('position', models.PositiveSmallIntegerField(default=0)),
                ('clicked', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'behavior_feed_impression_log',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='userinterestprofile',
            constraint=models.UniqueConstraint(fields=['user', 'date'], name='behavior_user_interest_user_date'),
        ),
        migrations.AddConstraint(
            model_name='entitypopularitysnapshot',
            constraint=models.UniqueConstraint(fields=['date', 'entity_type', 'entity_id'], name='behavior_entity_pop_date_entity'),
        ),
        migrations.AddConstraint(
            model_name='trendingsnapshotdaily',
            constraint=models.UniqueConstraint(fields=['date', 'entity_type', 'entity_id'], name='behavior_trending_date_entity'),
        ),
    ]
