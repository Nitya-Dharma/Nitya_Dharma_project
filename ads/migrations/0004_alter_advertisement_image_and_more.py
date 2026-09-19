# Identity-only production migration continuity.
#
# This migration preserves the production migration identity.
# The original historical operations are unavailable.
# No historical operations are being reconstructed or invented.
# This is an identity-only reconciliation migration.

from django.db import migrations


class Migration(migrations.Migration):
    """
    This migration preserves the production migration identity.
    The original historical operations are unavailable.
    No historical operations are being reconstructed or invented.
    This is an identity-only reconciliation migration.
    """

    dependencies = [
        ("ads", "0003_add_per_slot_images"),
    ]

    operations = []
