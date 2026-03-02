"""
Management command to manually create pages_page_role table if missing.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Create pages_page_role table if missing'

    def handle(self, *args, **options):
        cursor = connection.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='pages_page_role'
        """)
        if cursor.fetchone():
            self.stdout.write(self.style.SUCCESS('Table pages_page_role already exists'))
            return
        
        # Create table
        try:
            cursor.execute("""
                CREATE TABLE pages_page_role (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    public_id VARCHAR(36) UNIQUE,
                    page_id BIGINT NOT NULL REFERENCES pages_page(id) ON DELETE CASCADE,
                    pandit_id BIGINT NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
                    role VARCHAR(20) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS pages_pagero_page_pa_idx ON pages_page_role(page_id, pandit_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS pages_pagero_role_cr_idx ON pages_page_role(role, created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS pages_pagero_pandit_idx ON pages_page_role(pandit_id, role)")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_pandit_page_role ON pages_page_role(page_id, pandit_id)")
            self.stdout.write(self.style.SUCCESS('Successfully created pages_page_role table'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating table: {str(e)}'))

















