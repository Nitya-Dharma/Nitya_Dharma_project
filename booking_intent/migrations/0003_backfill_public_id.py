"""
Data migration to backfill public_id for existing BookingIntent records.
"""

from django.db import migrations, models, connection
from core.public_id import generate_public_id


def backfill_public_ids(apps, schema_editor):
    """Generate public_id for all existing booking intents."""
    # First, ensure the column exists (add it if migration 0002 didn't)
    # SQLite limitation: Can't add UNIQUE column directly, so add without UNIQUE first
    db_alias = schema_editor.connection.alias
    
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("PRAGMA table_info(booking_intent_bookingintent)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'public_id' not in columns:
            # Add the column without UNIQUE constraint (SQLite limitation)
            # Use raw SQL since schema_editor might have issues
            cursor.execute("ALTER TABLE booking_intent_bookingintent ADD COLUMN public_id VARCHAR(36) NULL")
            # Create index
            try:
                cursor.execute("CREATE INDEX booking_intent_bookingintent_public_id_idx ON booking_intent_bookingintent(public_id)")
            except:
                pass  # Index might already exist
    
    # Now backfill using raw SQL
    # Use Django's connection.execute() to avoid SQLite formatting issues
    db_alias = schema_editor.connection.alias
    from django.db import connections
    db_conn = connections[db_alias]
    
    with db_conn.cursor() as cursor:
        # Get all intents without public_id
        cursor.execute("SELECT id FROM booking_intent_bookingintent WHERE public_id IS NULL OR public_id = ''")
        intent_ids = [row[0] for row in cursor.fetchall()]
        
        # Update each intent with a new public_id
        # Use string formatting for UUID (safe since it's generated, not user input)
        for intent_id in intent_ids:
            public_id = generate_public_id()
            # Use direct SQL with string formatting (UUID is safe, not user input)
            sql = f"UPDATE booking_intent_bookingintent SET public_id = '{public_id}' WHERE id = {intent_id}"
            cursor.execute(sql)


def reverse_backfill(apps, schema_editor):
    """Reverse: Set public_id to None (but keep column)."""
    # Just set values to None, don't try to access the field if it doesn't exist
    with connection.cursor() as cursor:
        try:
            cursor.execute("UPDATE booking_intent_bookingintent SET public_id = NULL")
        except:
            pass  # Column might not exist


class Migration(migrations.Migration):

    dependencies = [
        ('booking_intent', '0002_add_public_id_fields'),
    ]

    operations = [
        migrations.RunPython(backfill_public_ids, reverse_backfill),
    ]

