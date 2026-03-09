"""
Phase 11F.1: Reset Django test database.

Run from project root when tests leave the test DB in a bad state
(e.g. "django_migrations already exists" or "Can't drop database").

Usage (from project root):
    python scripts/reset_test_db.py

Uses DB_HOST, DB_USER, DB_PASSWORD from .env (same as dev settings).
Requires MySQL (mysqlclient). The DB user must have CREATE/DROP on the test DB.
"""
import os
import sys

# Load .env from project root (parent of scripts/)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.chdir(_project_root)

try:
    from decouple import config
except ImportError:
    config = None

try:
    import MySQLdb
except ImportError:
    print("MySQLdb (mysqlclient) is required. Install: pip install mysqlclient")
    sys.exit(1)


def main():
    if config is None:
        print("python-decouple is required to read .env. Install: pip install python-decouple")
        sys.exit(1)

    host = config("DB_HOST", default="localhost")
    user = config("DB_USER", default="nitya_user")
    passwd = config("DB_PASSWORD", default="")
    port = config("DB_PORT", default="3306", cast=int)

    try:
        conn = MySQLdb.connect(
            host=host,
            user=user,
            passwd=passwd,
            port=port,
        )
    except MySQLdb.Error as e:
        print(f"Cannot connect to MySQL: {e}")
        sys.exit(1)

    cursor = conn.cursor()
    cursor.execute("DROP DATABASE IF EXISTS test_nityadharma_db;")
    conn.commit()
    cursor.close()
    conn.close()

    print("Test database dropped successfully.")


if __name__ == "__main__":
    main()
