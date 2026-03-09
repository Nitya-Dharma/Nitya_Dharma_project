# Phase 8 — Performance analysis (read-only SQL + config)
# Run: python manage.py shell -c "exec(open('phase8_analyze.py', encoding='utf-8').read())"

from django.db import connection

def run_sql(sql, params=None):
    with connection.cursor() as c:
        c.execute(sql, params or [])
        return c.fetchall()

print("=" * 60)
print("PHASE 8 — DATABASE & QUERY PERFORMANCE ANALYSIS")
print("=" * 60)

# STEP 1 — Heavy tables
print("\n--- STEP 1: HEAVY TABLES ---")
rows = run_sql("""
    SELECT table_name, table_rows, data_length, index_length
    FROM information_schema.tables
    WHERE table_schema = DATABASE()
    ORDER BY table_rows DESC
    LIMIT 25
""")
for r in rows:
    print("  %s | rows=%s | data=%s | index=%s" % (r[0], r[1], r[2], r[3]))

# STEP 2 — Slow query log
print("\n--- STEP 2: SLOW QUERY LOG ---")
for var in ["slow_query_log", "long_query_time", "log_output"]:
    r = run_sql("SHOW VARIABLES LIKE %s", [var])
    if r:
        print("  %s = %s" % (r[0][0], r[0][1]))

# STEP 3 — EXPLAIN Pandit search
print("\n--- STEP 3: EXPLAIN Pandit search (is_active=1 LIMIT 20) ---")
rows = run_sql("""
    EXPLAIN SELECT * FROM profiles_panditprofile
    WHERE is_profile_approved = 1 LIMIT 20
""")
for r in rows:
    print("  ", r)
# Also try is_active if column exists
try:
    rows2 = run_sql("EXPLAIN SELECT * FROM profiles_panditprofile WHERE is_active = 1 LIMIT 20")
    print("  (is_active):", rows2)
except Exception as e:
    print("  (is_active column not found, used is_profile_approved)")

# STEP 4 — EXPLAIN booking lookup
print("\n--- STEP 4: EXPLAIN booking lookup (pandit_id, created_at) ---")
rows = run_sql("""
    EXPLAIN SELECT * FROM booking_intent_bookingintent
    WHERE pandit_id = 1 ORDER BY created_at DESC LIMIT 10
""")
for r in rows:
    print("  ", r)

# STEP 5 — Index inspection
for table in ["profiles_panditprofile", "booking_intent_bookingintent", "pages_page", "referrals_referral_link"]:
    print("\n--- STEP 5: SHOW INDEX FROM %s ---" % table)
    try:
        rows = run_sql("SHOW INDEX FROM %s" % table)
        for r in rows:
            print("  ", r)
    except Exception as e:
        print("  ERROR:", e)

# STEP 9 — MySQL config
print("\n--- STEP 9: MYSQL CONFIG ---")
for var in ["innodb_buffer_pool_size", "max_connections", "query_cache_size", "query_cache_type"]:
    try:
        r = run_sql("SHOW VARIABLES LIKE %s", [var])
        if r:
            print("  %s = %s" % (r[0][0], r[0][1]))
        else:
            print("  %s = (not found)" % var)
    except Exception as e:
        print("  %s: %s" % (var, e))

print("\n" + "=" * 60)
