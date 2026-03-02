import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print('[OK] Database connection successful')
print(f'[OK] Tables in database: {len(tables)} (expected: 0)')
if len(tables) == 0:
    print('[OK] No tables created yet (as expected)')
else:
    print(f'[WARN] Found tables: {[t[0] for t in tables]}')

