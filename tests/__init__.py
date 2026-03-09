# Project-level tests package
#
# If tests fail due to test database state (e.g. "django_migrations already exists"
# or "Can't drop database"), reset the test DB then run tests again:
#
#   python scripts/reset_test_db.py
#   python manage.py test --noinput tests.navigation
#   python manage.py test --noinput tests.user_journey
#   python manage.py test --noinput tests.load_testing
#
# Avoid --keepdb when the test DB is in an inconsistent state; use --noinput
# so Django can create/destroy the test database cleanly.
