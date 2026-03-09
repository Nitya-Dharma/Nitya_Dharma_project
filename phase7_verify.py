# Phase 7 — Data Integrity & Geo-Performance Verification (read-only)
# Run with: python manage.py shell < phase7_verify.py
# Or: python manage.py shell then paste this file content

from django.db import connection

def run_sql(sql, params=None, fetch=True):
    with connection.cursor() as c:
        c.execute(sql, params or [])
        return c.fetchall() if fetch else None

print("=" * 60)
print("PHASE 7 — MYSQL DATA INTEGRITY + GEO PERFORMANCE VERIFICATION")
print("=" * 60)

# STEP 1 — Tables
print("\n--- STEP 1: SHOW TABLES ---")
rows = run_sql("SHOW TABLES")
tables = [r[0] for r in rows]
print(f"Total tables: {len(tables)}")
for t in sorted(tables):
    print(f"  {t}")
expected = [
    "accounts_user", "profiles_panditprofile", "pages_page", "masterdata_state",
    "masterdata_city", "referrals_referral", "booking_intent_bookingintent",
    "reviews_review", "notifications_notification"
]
missing = [e for e in expected if not any(e in t for t in tables)]
if missing:
    print("  (Expected names may differ; check list above)")

# STEP 2 — Row counts
print("\n--- STEP 2: ROW COUNTS ---")
count_tables = [
    "accounts_user", "profiles_panditprofile", "pages_page",
    "referrals_referral", "reviews_review", "booking_intent_bookingintent"
]
counts = {}
for t in count_tables:
    try:
        r = run_sql(f"SELECT COUNT(*) FROM {t}")
        counts[t] = r[0][0] if r else 0
        print(f"  {t}: {counts[t]}")
    except Exception as e:
        counts[t] = str(e)
        print(f"  {t}: ERROR - {e}")

# STEP 3 — FK integrity (orphans)
print("\n--- STEP 3: FOREIGN KEY INTEGRITY (orphans) ---")
q1 = """
SELECT COUNT(*) FROM profiles_panditprofile p
LEFT JOIN accounts_user u ON p.user_id = u.id WHERE u.id IS NULL
"""
q2 = """
SELECT COUNT(*) FROM pages_page p
LEFT JOIN accounts_user u ON p.owner_id = u.id WHERE u.id IS NULL
"""
q3 = """
SELECT COUNT(*) FROM booking_intent_bookingintent b
LEFT JOIN profiles_panditprofile p ON b.pandit_id = p.id WHERE p.id IS NULL
"""
for name, q in [("PanditProfile without User", q1), ("Page without owner", q2), ("BookingIntent without Pandit", q3)]:
    try:
        r = run_sql(q)
        n = r[0][0] if r else 0
        print(f"  {name}: {n} (expect 0)")
    except Exception as e:
        print(f"  {name}: ERROR - {e}")

# STEP 4 — Unique constraint (duplicates)
print("\n--- STEP 4: UNIQUE CONSTRAINT VALIDATION ---")
dup_checks = [
    ("profiles_panditprofile", "user_id"),
    ("accounts_user", "email"),
    ("pages_page", "slug"),
]
for table, col in dup_checks:
    try:
        q = f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col} HAVING COUNT(*) > 1"
        r = run_sql(q)
        print(f"  {table}.{col} duplicates: {len(r)} row(s) (expect 0)")
        if r:
            for row in r[:5]:
                print(f"    -> {row}")
    except Exception as e:
        print(f"  {table}.{col}: ERROR - {e}")

# STEP 5 — Geo master data
print("\n--- STEP 5: GEO DATA (state/city) ---")
try:
    r = run_sql("SELECT COUNT(*) FROM masterdata_state")
    print(f"  masterdata_state: {r[0][0]}")
except Exception as e:
    print(f"  masterdata_state: ERROR - {e}")
try:
    r = run_sql("SELECT COUNT(*) FROM masterdata_city")
    print(f"  masterdata_city: {r[0][0]}")
except Exception as e:
    print(f"  masterdata_city: ERROR - {e}")
try:
    r = run_sql("SELECT name FROM masterdata_state ORDER BY name LIMIT 15")
    print("  Sample states:", [x[0] for x in r])
except Exception as e:
    print("  Sample states: ERROR -", e)

# STEP 6 — Geo distribution (profiles by state_code)
print("\n--- STEP 6: GEO DISTRIBUTION (profiles by state_code) ---")
try:
    r = run_sql("""
        SELECT state_code, COUNT(*) FROM profiles_panditprofile
        GROUP BY state_code ORDER BY COUNT(*) DESC LIMIT 15
    """)
    for row in r:
        print(f"  {row[0]}: {row[1]}")
except Exception as e:
    print("  ERROR -", e)

# STEP 7 — EXPLAIN search query
print("\n--- STEP 7: QUERY PLAN (geo search pattern) ---")
try:
    r = run_sql("""
        EXPLAIN SELECT * FROM profiles_panditprofile
        WHERE state_code='TG' AND city='Hyderabad' AND is_active=1
    """)
    for row in r:
        print("  ", row)
except Exception as e:
    print("  ERROR -", e)

# STEP 8 — Indexes on profiles_panditprofile
print("\n--- STEP 8: INDEXES ON profiles_panditprofile ---")
try:
    r = run_sql("SHOW INDEX FROM profiles_panditprofile")
    for row in r:
        print("  ", row)
except Exception as e:
    print("  ERROR -", e)

# STEP 9 — Slow query config
print("\n--- STEP 9: SLOW QUERY CONFIG ---")
for var in ["slow_query_log", "long_query_time"]:
    try:
        r = run_sql("SHOW VARIABLES LIKE %s", [var])
        print("  ", r[0] if r else "N/A")
    except Exception as e:
        print(f"  {var}: ERROR - {e}")

# STEP 10 — ORM (run in same shell so models already loaded)
print("\n--- STEP 10: DJANGO ORM VERIFICATION ---")
try:
    from accounts.models import User
    from profiles.models import PanditProfile
    from pages.models import Page
    print("  User.objects.count():", User.objects.count())
    print("  PanditProfile.objects.count():", PanditProfile.objects.count())
    print("  Page.objects.count():", Page.objects.count())
    qs = PanditProfile.objects.filter(state_code="TG")[:5]
    print("  PanditProfile.objects.filter(state_code='TG')[:5]:", list(qs.values_list("id", "user_id", "state_code", "city")[:5]))
except Exception as e:
    print("  ORM ERROR:", e)

print("\n" + "=" * 60)
print("Phase 7 verification script finished. See report above.")
print("=" * 60)
