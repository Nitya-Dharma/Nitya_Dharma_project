# Phase 14.x: Advanced behavior data collection. Additive only — no changes to existing tables.
# New tables: UserContentInteraction, UserFeedImpression, UserSessionAnalytics, UserInterestSignal.
# Raw events older than 90 days may be archived later. Do not implement deletion yet.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("behavior_engine", "0002_phase14_user_behavior_event"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserContentInteraction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_id", models.CharField(blank=True, db_index=True, max_length=120, null=True)),
                ("content_type", models.CharField(db_index=True, max_length=50)),
                ("content_id", models.IntegerField(db_index=True)),
                ("interaction_type", models.CharField(db_index=True, max_length=50)),
                ("dwell_time_ms", models.IntegerField(blank=True, null=True)),
                ("scroll_depth", models.IntegerField(blank=True, null=True)),
                ("position_in_list", models.IntegerField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="behavior_content_interactions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "behavior_user_content_interaction",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="usercontentinteraction",
            index=models.Index(fields=["user", "created_at"], name="behavior_us_user_id_created_idx"),
        ),
        migrations.AddIndex(
            model_name="usercontentinteraction",
            index=models.Index(fields=["content_type", "content_id"], name="behavior_us_content_type_id_idx"),
        ),
        migrations.AddIndex(
            model_name="usercontentinteraction",
            index=models.Index(fields=["interaction_type", "created_at"], name="behavior_us_interaction_created_idx"),
        ),
        migrations.CreateModel(
            name="UserFeedImpression",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_id", models.CharField(blank=True, db_index=True, max_length=120, null=True)),
                ("content_type", models.CharField(db_index=True, max_length=50)),
                ("content_id", models.IntegerField(db_index=True)),
                ("feed_type", models.CharField(db_index=True, max_length=50)),
                ("feed_position", models.IntegerField()),
                ("was_clicked", models.BooleanField(default=False)),
                ("was_booked", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="behavior_feed_impressions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "behavior_user_feed_impression",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="userfeedimpression",
            index=models.Index(fields=["user", "created_at"], name="behavior_us_user_id_created_feed_idx"),
        ),
        migrations.AddIndex(
            model_name="userfeedimpression",
            index=models.Index(fields=["feed_type", "created_at"], name="behavior_us_feed_type_created_idx"),
        ),
        migrations.CreateModel(
            name="UserSessionAnalytics",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_id", models.CharField(db_index=True, max_length=120)),
                ("session_start", models.DateTimeField()),
                ("session_end", models.DateTimeField()),
                ("events_count", models.IntegerField(default=0)),
                ("page_views", models.IntegerField(default=0)),
                ("search_queries", models.IntegerField(default=0)),
                ("total_dwell_time_ms", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="behavior_session_analytics", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "behavior_user_session_analytics",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="usersessionanalytics",
            index=models.Index(fields=["session_id"], name="behavior_us_session_id_idx"),
        ),
        migrations.AddIndex(
            model_name="usersessionanalytics",
            index=models.Index(fields=["user", "created_at"], name="behavior_us_user_created_sess_idx"),
        ),
        migrations.CreateModel(
            name="UserInterestSignal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("interest_type", models.CharField(db_index=True, max_length=50)),
                ("interest_value", models.CharField(db_index=True, max_length=100)),
                ("score", models.FloatField(default=0.0)),
                ("last_updated", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="behavior_interest_signals", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "behavior_user_interest_signal",
                "ordering": ["user", "interest_type"],
                "unique_together": {("user", "interest_type", "interest_value")},
            },
        ),
        migrations.AddIndex(
            model_name="userinterestsignal",
            index=models.Index(fields=["user", "interest_type"], name="behavior_us_user_interest_type_idx"),
        ),
    ]
