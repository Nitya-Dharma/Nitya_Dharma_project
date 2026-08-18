# Additive phone verification flags for post-registration OTP flow.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_phone_verified",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Whether the user has verified their mobile number via OTP.",
                verbose_name="Phone Verified",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="phone_verified_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when mobile OTP verification succeeded.",
                null=True,
                verbose_name="Phone Verified At",
            ),
        ),
    ]
