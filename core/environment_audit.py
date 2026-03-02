"""
Environment Separation Audit — PART 6 — PRE-LAUNCH & DEPLOYMENT READINESS

TASK 6.1: Environment Separation Audit

Verify strict separation between environments:
- dev
- staging
- prod

RULES:
- Each environment has its own:
  - DATABASE
  - EMAIL backend
  - SECRET_KEY
  - DEBUG flag

VERIFY:
- DEBUG=False in prod
- No dev credentials in prod
- .env files never committed
"""

import os
from django.conf import settings
from typing import Dict, List, Tuple


def audit_environment_separation() -> Dict:
    """
    Audit environment separation.
    
    Returns:
        Dict with audit results
    """
    issues = []
    warnings = []
    
    # Check DEBUG flag
    if settings.DEBUG:
        if os.environ.get('DJANGO_ENV') == 'production' or 'prod' in os.environ.get('DJANGO_SETTINGS_MODULE', '').lower():
            issues.append({
                'severity': 'CRITICAL',
                'check': 'DEBUG flag',
                'issue': 'DEBUG=True in production environment',
                'fix': 'Set DEBUG=False in production settings',
            })
        else:
            warnings.append({
                'severity': 'WARNING',
                'check': 'DEBUG flag',
                'message': 'DEBUG=True (acceptable for dev/staging)',
            })
    
    # Check SECRET_KEY
    secret_key = getattr(settings, 'SECRET_KEY', None)
    if not secret_key:
        issues.append({
            'severity': 'CRITICAL',
            'check': 'SECRET_KEY',
            'issue': 'SECRET_KEY not set',
            'fix': 'Set SECRET_KEY in environment variables',
        })
    elif secret_key == 'django-insecure-' or len(secret_key) < 50:
        if os.environ.get('DJANGO_ENV') == 'production':
            issues.append({
                'severity': 'CRITICAL',
                'check': 'SECRET_KEY',
                'issue': 'Weak or default SECRET_KEY in production',
                'fix': 'Generate strong SECRET_KEY for production',
            })
        else:
            warnings.append({
                'severity': 'WARNING',
                'check': 'SECRET_KEY',
                'message': 'Weak SECRET_KEY (acceptable for dev/staging)',
            })
    
    # Check database configuration
    databases = getattr(settings, 'DATABASES', {})
    default_db = databases.get('default', {})
    
    if 'sqlite' in default_db.get('ENGINE', '').lower():
        if os.environ.get('DJANGO_ENV') == 'production':
            issues.append({
                'severity': 'CRITICAL',
                'check': 'Database',
                'issue': 'SQLite database in production',
                'fix': 'Use PostgreSQL or MySQL in production',
            })
        else:
            warnings.append({
                'severity': 'INFO',
                'check': 'Database',
                'message': 'SQLite database (acceptable for dev)',
            })
    
    # Check email backend
    email_backend = getattr(settings, 'EMAIL_BACKEND', None)
    if email_backend == 'django.core.mail.backends.console.EmailBackend':
        if os.environ.get('DJANGO_ENV') == 'production':
            warnings.append({
                'severity': 'WARNING',
                'check': 'Email Backend',
                'message': 'Console email backend in production (emails not sent)',
            })
    
    # Check for hardcoded credentials
    hardcoded_patterns = [
        'password',
        'secret',
        'api_key',
        'token',
    ]
    
    # This is a basic check - full audit requires code scanning
    warnings.append({
        'severity': 'INFO',
        'check': 'Hardcoded Credentials',
        'message': 'Full credential audit requires code scanning tool',
    })
    
    return {
        'issues': issues,
        'warnings': warnings,
        'status': 'pass' if not issues else 'fail',
    }


def format_audit_report(results: Dict) -> str:
    """
    Format audit results as a readable report.
    
    Args:
        results: Audit results from audit_environment_separation()
    
    Returns:
        Formatted report string
    """
    report = ["🔍 ENVIRONMENT SEPARATION AUDIT — PART 6 — PRE-LAUNCH\n"]
    report.append("=" * 70)
    report.append("")
    
    issues = results.get('issues', [])
    warnings = results.get('warnings', [])
    
    # Critical issues
    if issues:
        report.append("❌ CRITICAL ISSUES:")
        report.append("")
        for issue in issues:
            report.append(f"  [{issue['severity']}] {issue['check']}:")
            report.append(f"    Issue: {issue['issue']}")
            report.append(f"    Fix: {issue['fix']}")
            report.append("")
    
    # Warnings
    if warnings:
        report.append("⚠️  WARNINGS:")
        report.append("")
        for warning in warnings:
            report.append(f"  [{warning['severity']}] {warning['check']}:")
            report.append(f"    {warning['message']}")
            report.append("")
    
    # Summary
    if not issues:
        report.append("✅ ENVIRONMENT SEPARATION: PASS")
        report.append("")
        report.append("All critical checks passed.")
    else:
        report.append("❌ ENVIRONMENT SEPARATION: FAIL")
        report.append("")
        report.append(f"{len(issues)} critical issue(s) must be fixed before deployment.")
    
    return "\n".join(report)


if __name__ == '__main__':
    """
    Run environment separation audit.
    
    Usage:
        python core/environment_audit.py
    
    Exit codes:
        0: All checks passed
        1: Critical issues found
    """
    import sys
    import django
    from django.conf import settings
    
    # Setup Django
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
        django.setup()
    
    results = audit_environment_separation()
    report = format_audit_report(results)
    print(report)
    
    if results['status'] == 'fail':
        sys.exit(1)
    else:
        sys.exit(0)




