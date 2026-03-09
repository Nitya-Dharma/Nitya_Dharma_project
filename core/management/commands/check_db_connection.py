"""
Print current database connection settings (host, name) to verify which DB the app is using.
Useful for checking that Railway deployment is connected to Railway's MySQL.

Usage:
    python manage.py check_db_connection
    railway ssh -- python manage.py check_db_connection
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Print database connection host and name (to verify Railway vs local DB)"

    def handle(self, *args, **options):
        c = connection.settings_dict
        host = c.get("HOST") or "(none)"
        name = c.get("NAME") or "(none)"
        engine = c.get("ENGINE", "")
        self.stdout.write(f"DB engine: {engine}")
        self.stdout.write(f"DB host:  {host}")
        self.stdout.write(f"DB name:  {name}")
        if "railway" in str(host).lower() or "railway.internal" in str(host).lower():
            self.stdout.write(self.style.SUCCESS("Connected to Railway database."))
        else:
            self.stdout.write(self.style.WARNING("Not Railway (e.g. local or other)."))
