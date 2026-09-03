from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0004_campaign_and_ad_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdSet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "target_urls",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Optional URL path list (configuration only).",
                    ),
                ),
                (
                    "target_roles",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Optional role list (configuration only).",
                    ),
                ),
                (
                    "target_locations",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Optional city names (configuration only).",
                    ),
                ),
                (
                    "placements",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Optional placement list (configuration only).",
                    ),
                ),
                (
                    "pricing_model",
                    models.CharField(
                        choices=[("CPM", "CPM"), ("IMPRESSION", "IMPRESSION")],
                        default="IMPRESSION",
                        max_length=20,
                    ),
                ),
                ("cpm_rate", models.FloatField(blank=True, null=True)),
                ("max_impressions", models.BigIntegerField(blank=True, null=True)),
                ("frequency_cap", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ad_sets",
                        to="ads.campaign",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["campaign"], name="ads_adset_campaig_65133e_idx"),
                    models.Index(fields=["is_active"], name="ads_adset_is_acti_0ea7ba_idx"),
                    models.Index(fields=["campaign", "is_active"], name="ads_adset_campaig_0b9c20_idx"),
                ],
            },
        ),
        migrations.AddField(
            model_name="advertisement",
            name="ad_set",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ads",
                to="ads.adset",
            ),
        ),
    ]
