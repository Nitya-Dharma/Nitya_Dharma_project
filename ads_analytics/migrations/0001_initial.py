# Advertisement analytics: event and aggregation models

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("ads", "0003_add_per_slot_images"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AdImpression",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("campaign_id", models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ("placement_position", models.CharField(db_index=True, max_length=50)),
                ("page_type", models.CharField(blank=True, db_index=True, max_length=50)),
                ("page_url", models.CharField(blank=True, max_length=2048)),
                ("pandit_id", models.PositiveIntegerField(blank=True, db_index=True, null=True)),
                ("session_id", models.CharField(blank=True, db_index=True, max_length=40)),
                ("device_type", models.CharField(blank=True, db_index=True, max_length=20)),
                ("viewer_city", models.CharField(blank=True, db_index=True, max_length=150)),
                ("viewer_area", models.CharField(blank=True, max_length=150)),
                ("viewer_state", models.CharField(blank=True, db_index=True, max_length=150)),
                ("viewer_country", models.CharField(blank=True, db_index=True, max_length=150)),
                ("referrer_source", models.CharField(blank=True, max_length=500)),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("ad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="analytics_impressions", to="ads.advertisement")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ad_impressions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-timestamp"],
                "app_label": "ads_analytics",
            },
        ),
        migrations.CreateModel(
            name="AdClick",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("campaign_id", models.CharField(blank=True, db_index=True, max_length=100, null=True)),
                ("placement_position", models.CharField(db_index=True, max_length=50)),
                ("page_type", models.CharField(blank=True, db_index=True, max_length=50)),
                ("pandit_id", models.PositiveIntegerField(blank=True, db_index=True, null=True)),
                ("session_id", models.CharField(blank=True, db_index=True, max_length=40)),
                ("viewer_city", models.CharField(blank=True, db_index=True, max_length=150)),
                ("viewer_area", models.CharField(blank=True, max_length=150)),
                ("viewer_state", models.CharField(blank=True, max_length=150)),
                ("viewer_country", models.CharField(blank=True, max_length=150)),
                ("referrer_source", models.CharField(blank=True, max_length=500)),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("ad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="analytics_clicks", to="ads.advertisement")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ad_clicks", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-timestamp"],
                "app_label": "ads_analytics",
            },
        ),
        migrations.CreateModel(
            name="AdConversionIntent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pandit_id", models.PositiveIntegerField(blank=True, db_index=True, null=True)),
                ("conversion_type", models.CharField(choices=[("booking_intent", "Booking intent"), ("profile_view", "Profile view"), ("other", "Other")], db_index=True, max_length=50)),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("ad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="analytics_conversions", to="ads.advertisement")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ad_conversion_intents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-timestamp"],
                "app_label": "ads_analytics",
            },
        ),
        migrations.CreateModel(
            name="AdRevenueEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("billing_model", models.CharField(choices=[("CPM", "CPM"), ("CPC", "CPC"), ("Sponsored", "Sponsored"), ("Featured", "Featured")], db_index=True, max_length=30)),
                ("impressions", models.PositiveIntegerField(default=0)),
                ("clicks", models.PositiveIntegerField(default=0)),
                ("revenue_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("ad", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="revenue_events", to="ads.advertisement")),
            ],
            options={
                "ordering": ["-timestamp"],
                "app_label": "ads_analytics",
            },
        ),
        migrations.CreateModel(
            name="AdLocationStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True)),
                ("viewer_city", models.CharField(blank=True, db_index=True, max_length=150)),
                ("viewer_state", models.CharField(blank=True, db_index=True, max_length=150)),
                ("impressions", models.PositiveIntegerField(default=0)),
                ("clicks", models.PositiveIntegerField(default=0)),
            ],
            options={
                "ordering": ["-date", "viewer_city", "viewer_state"],
                "unique_together": {("date", "viewer_city", "viewer_state")},
                "app_label": "ads_analytics",
            },
        ),
        migrations.CreateModel(
            name="AdPlacementStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True)),
                ("placement_position", models.CharField(db_index=True, max_length=50)),
                ("impressions", models.PositiveIntegerField(default=0)),
                ("clicks", models.PositiveIntegerField(default=0)),
            ],
            options={
                "ordering": ["-date", "placement_position"],
                "unique_together": {("date", "placement_position")},
                "app_label": "ads_analytics",
            },
        ),
        migrations.CreateModel(
            name="AdDailyStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True)),
                ("placement_position", models.CharField(blank=True, db_index=True, max_length=50, null=True)),
                ("impressions", models.PositiveIntegerField(default=0)),
                ("clicks", models.PositiveIntegerField(default=0)),
                ("unique_users", models.PositiveIntegerField(default=0)),
                ("viewer_city", models.CharField(blank=True, max_length=150, null=True)),
                ("viewer_state", models.CharField(blank=True, max_length=150, null=True)),
                ("ad", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="daily_stats", to="ads.advertisement")),
            ],
            options={
                "ordering": ["-date", "ad"],
                "unique_together": {("date", "ad", "placement_position", "viewer_city", "viewer_state")},
                "app_label": "ads_analytics",
            },
        ),
        migrations.AddIndex(
            model_name="adimpression",
            index=models.Index(fields=["ad", "timestamp"], name="ads_analyti_ad_id_0a2b0d_idx"),
        ),
        migrations.AddIndex(
            model_name="adimpression",
            index=models.Index(fields=["placement_position", "timestamp"], name="ads_analyti_placeme_8c0e2a_idx"),
        ),
        migrations.AddIndex(
            model_name="adimpression",
            index=models.Index(fields=["viewer_city", "timestamp"], name="ads_analyti_viewer__d4f1a3_idx"),
        ),
        migrations.AddIndex(
            model_name="adimpression",
            index=models.Index(fields=["pandit_id", "timestamp"], name="ads_analyti_pandit__e5b2c4_idx"),
        ),
        migrations.AddIndex(
            model_name="adclick",
            index=models.Index(fields=["ad", "timestamp"], name="ads_analyti_ad_id_1c3d4e_idx"),
        ),
        migrations.AddIndex(
            model_name="adclick",
            index=models.Index(fields=["placement_position", "timestamp"], name="ads_analyti_placeme_9d1f3b_idx"),
        ),
        migrations.AddIndex(
            model_name="adclick",
            index=models.Index(fields=["viewer_city", "timestamp"], name="ads_analyti_viewer__e6a3b5_idx"),
        ),
        migrations.AddIndex(
            model_name="adclick",
            index=models.Index(fields=["pandit_id", "timestamp"], name="ads_analyti_pandit__f7b4c6_idx"),
        ),
        migrations.AddIndex(
            model_name="addailystats",
            index=models.Index(fields=["date", "ad"], name="ads_analyti_date_2e5f7d_idx"),
        ),
        migrations.AddIndex(
            model_name="addailystats",
            index=models.Index(fields=["date", "placement_position"], name="ads_analyti_placeme_a8d2e9_idx"),
        ),
    ]
