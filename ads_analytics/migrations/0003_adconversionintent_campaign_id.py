# Generated manually for additive AdConversionIntent.campaign_id only.
# Pre-existing index-rename drift detected by makemigrations is intentionally
# excluded from this migration (not fixed here).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "ads_analytics",
            "0002_rename_ads_analyti_ad_id_1c3d4e_idx_ads_analyti_ad_id_6f922a_idx_and_more",
        ),
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
