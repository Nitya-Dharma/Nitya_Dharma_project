# Generated for additive AdLead only.
# Depends on original-present parents: ads.0003 (Advertisement already exists
# via ads.0001) and ads_analytics.0003 (AdConversionIntent.campaign_id).
# Does not depend on deleted ads.0005_adset_and_ad_link or Native ads.0070.
# Pre-existing index-rename drift is intentionally excluded (same policy as 0003).

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0003_add_per_slot_images"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ads_analytics", "0003_adconversionintent_campaign_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdLead",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "campaign_id",
                    models.CharField(
                        blank=True, db_index=True, max_length=100, null=True
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("whatsapp_cta", "WhatsApp CTA"),
                            ("booking_intent", "Booking Intent"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("contacted", "Contacted"),
                            ("follow_up", "Follow up"),
                            ("converted", "Converted"),
                            ("lost", "Lost"),
                        ],
                        default="new",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "advertisement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ad_leads",
                        to="ads.advertisement",
                    ),
                ),
                (
                    "source_conversion",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ad_lead",
                        to="ads_analytics.adconversionintent",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ad_leads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "app_label": "ads_analytics",
            },
        ),
        migrations.AddIndex(
            model_name="adlead",
            index=models.Index(
                fields=["status", "created_at"],
                name="ads_analyti_status_e80d46_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="adlead",
            index=models.Index(
                fields=["advertisement", "created_at"],
                name="ads_analyti_adverti_e6a145_idx",
            ),
        ),
    ]
