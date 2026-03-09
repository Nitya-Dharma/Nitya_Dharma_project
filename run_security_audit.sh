#!/usr/bin/env bash
# Phase 9.5: Run full security audit (bandit, safety, pip-audit, django check --deploy, pytest security tests)
# Usage: ./run_security_audit.sh   (or bash run_security_audit.sh)
set -e
cd "$(dirname "$0")"
echo "=== Activating venv ==="
if [ -n "$VIRTUAL_ENV" ]; then
  echo "Already in venv: $VIRTUAL_ENV"
else
  [ -d "venv/Scripts" ] && source venv/Scripts/activate || source venv/bin/activate
fi
echo "=== 1. Bandit ==="
bandit -r . -x ./venv,./.git,./__pycache__,./node_modules,./staticfiles -f json -o bandit_security_report.json || true
bandit -r . -x ./venv,./.git,./__pycache__,./node_modules,./staticfiles -f txt -o bandit_security_report.txt || true
echo "=== 2. Safety ==="
safety check --full-report > safety_vulnerability_report.txt 2>&1 || true
echo "=== 3. pip-audit ==="
pip-audit > pip_audit_report.txt 2>&1 || true
echo "=== 4. Django check --deploy ==="
python manage.py check --deploy > django_security_check_report.txt 2>&1 || true
echo "=== 5. Pytest security tests ==="
pytest tests/security/ -v --tb=short || true
echo "=== Security audit complete. See SECURITY_AUDIT_REPORT.md and *.txt / *.json ==="
