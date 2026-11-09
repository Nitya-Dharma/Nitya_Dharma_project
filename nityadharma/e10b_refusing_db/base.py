"""
SQLite-shaped Django DB backend that refuses every connection.

E10B-only. Satisfies Django's DATABASES requirement without offering a
usable database. Does not import nityadharma.settings.
"""

from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper


class ProbeDatabaseDisabled(RuntimeError):
    """Raised if anything attempts to open a DB connection under E10B probe settings."""


class DatabaseWrapper(SQLiteDatabaseWrapper):
    vendor = "e10b_probe_db_disabled"
    display_name = "Disabled (E10B Celery worker probe)"

    def get_new_connection(self, conn_params):
        raise ProbeDatabaseDisabled(
            "nityadharma.e10b_refusing_db forbids database connections."
        )

    def create_cursor(self, name=None):
        raise ProbeDatabaseDisabled(
            "nityadharma.e10b_refusing_db forbids database cursors."
        )
