"""
Management command to manually create pages_page_audit_log table if missing.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Create pages_page_audit_log table if missing'

    def handle(self, *args, **options):
        cursor = connection.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='pages_page_audit_log'
        """)
        if cursor.fetchone():
            self.stdout.write(self.style.SUCCESS('Table pages_page_audit_log already exists'))
            return
        
        # Create table
        try:
            cursor.execute("""
                CREATE TABLE pages_page_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_id BIGINT NOT NULL REFERENCES pages_page(id) ON DELETE CASCADE,
                    action VARCHAR(30) NOT NULL,
                    performed_by_id BIGINT NOT NULL REFERENCES accounts_user(id),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS pages_page__page_id_idx ON pages_page_audit_log(page_id, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS pages_page__action__idx ON pages_page_audit_log(action, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS pages_page__perfor_idx ON pages_page_audit_log(performed_by_id, created_at)")
            self.stdout.write(self.style.SUCCESS('Successfully created pages_page_audit_log table'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating table: {str(e)}'))

