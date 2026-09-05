# Generated manually for additive AdConversionIntent.campaign_id only.
# Pre-existing index-rename drift detected by makemigrations is intentionally
# excluded from this migration (not fixed here).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ads_analytics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="adconversionintent",
            name="campaign_id",
            field=models.CharField(
                blank=True, db_index=True, max_length=100, null=True
            ),
        ),
    ]
