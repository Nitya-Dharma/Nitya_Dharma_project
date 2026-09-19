from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ads", "0004_alter_advertisement_image_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Campaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Active"),
                            ("PAUSED", "Paused"),
                            ("ENDED", "Ended"),
                        ],
                        db_index=True,
                        default="PAUSED",
                        max_length=20,
                    ),
                ),
                ("priority", models.PositiveIntegerField(default=1)),
                ("start_date", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("end_date", models.DateTimeField(blank=True, db_index=True, null=True)),
                (
                    "daily_budget",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                (
                    "total_budget",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
                ),
                ("spent_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                (
                    "target_roles",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Optional campaign-level role targeting. Example: ['user', 'pandit']",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="advertisement",
            name="campaign",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="advertisements",
                to="ads.campaign",
            ),
        ),
    ]
