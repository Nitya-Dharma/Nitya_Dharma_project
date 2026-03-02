"""
Management command to manually add followers_count column if missing.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Add followers_count column to pages_page table if missing'

    def handle(self, *args, **options):
        cursor = connection.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(pages_page)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'followers_count' in columns:
            self.stdout.write(self.style.SUCCESS('Column followers_count already exists'))
            return
        
        # Add column
        try:
            cursor.execute("ALTER TABLE pages_page ADD COLUMN followers_count INTEGER NOT NULL DEFAULT 0")
            cursor.execute("CREATE INDEX IF NOT EXISTS pages_page_followers_count_idx ON pages_page(followers_count)")
            self.stdout.write(self.style.SUCCESS('Successfully added followers_count column'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error adding column: {str(e)}'))

















