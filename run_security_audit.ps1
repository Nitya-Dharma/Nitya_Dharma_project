# Phase 9.5: Run full security audit (Windows PowerShell)
# Usage: .\run_security_audit.ps1
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
Write-Host "=== Activating venv ==="
& .\venv\Scripts\Activate.ps1
Write-Host "=== 1. Bandit ==="
bandit -r . -x ./venv,./.git,./__pycache__,./node_modules,./staticfiles -f json -o bandit_security_report.json
bandit -r . -x ./venv,./.git,./__pycache__,./node_modules,./staticfiles -f txt -o bandit_security_report.txt
Write-Host "=== 2. Safety ==="
safety check --full-report 2>&1 | Out-File -FilePath safety_vulnerability_report.txt -Encoding utf8
Write-Host "=== 3. pip-audit ==="
pip-audit 2>&1 | Out-File -FilePath pip_audit_report.txt -Encoding utf8
Write-Host "=== 4. Django check --deploy ==="
python manage.py check --deploy 2>&1 | Out-File -FilePath django_security_check_report.txt -Encoding utf8
Write-Host "=== 5. Pytest security tests ==="
pytest tests/security/ -v --tb=short
Write-Host "=== Security audit complete. See SECURITY_AUDIT_REPORT.md and report files ==="
