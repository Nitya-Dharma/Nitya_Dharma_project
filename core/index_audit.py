"""
Index Audit & Enforcement — PART 5 — PRODUCTION READINESS

TASK 5.1: Index Audit & Enforcement

This module audits and enforces indexes for all high-read paths.

MANDATORY INDEXES:
- public_id (unique, already indexed)
- status / visibility_status (for filtering)
- created_at (for sorting)
- foreign keys used in filters (for joins)

RULE:
- No unindexed filter used in search, dashboards, or feeds
"""

from typing import List, Dict, Tuple
from django.db import models
from django.apps import apps


# Models that require mandatory indexes
HIGH_READ_MODELS = [
    'accounts.User',
    'profiles.PanditProfile',
    'pages.TemplePage',
    'pages.BrandPage',
    'pages.ServicePage',
    'pages.PagePost',
    'pages.PageReview',
    'booking_intent.BookingIntent',
    'referrals.Referral',
    'engagement.EngagementEvent',
    'notifications.Notification',
]

# Mandatory index patterns
MANDATORY_INDEXES = {
    'public_id': {
        'type': 'unique',
        'reason': 'Used in URLs and API lookups',
        'required': True,
    },
    'status': {
        'type': 'index',
        'reason': 'Used in filtering active/inactive entities',
        'required': True,
    },
    'created_at': {
        'type': 'index',
        'reason': 'Used in sorting and pagination',
        'required': True,
    },
    'user_id': {
        'type': 'index',
        'reason': 'Foreign key used in filters',
        'required': True,
    },
    'pandit_id': {
        'type': 'index',
        'reason': 'Foreign key used in filters',
        'required': True,
    },
    'page_id': {
        'type': 'index',
        'reason': 'Foreign key used in filters',
        'required': True,
    },
}


def get_model_indexes(model_class) -> List[Dict]:
    """
    Get all indexes defined for a model.
    
    Args:
        model_class: Django model class
    
    Returns:
        List of index definitions
    """
    indexes = []
    
    # Check Meta.indexes
    if hasattr(model_class._meta, 'indexes'):
        for index in model_class._meta.indexes:
            indexes.append({
                'type': 'composite' if len(index.fields) > 1 else 'single',
                'fields': index.fields,
                'name': index.name,
                'source': 'Meta.indexes',
            })
    
    # Check db_index=True fields
    for field in model_class._meta.get_fields():
        if hasattr(field, 'db_index') and field.db_index:
            indexes.append({
                'type': 'field',
                'fields': [field.name],
                'name': f'{field.name}_idx',
                'source': 'db_index=True',
            })
    
    # Check unique constraints (which create indexes)
    if hasattr(model_class._meta, 'unique_together'):
        for unique_fields in model_class._meta.unique_together:
            indexes.append({
                'type': 'unique',
                'fields': list(unique_fields),
                'name': f'{"_".join(unique_fields)}_unique',
                'source': 'unique_together',
            })
    
    return indexes


def audit_model_indexes(model_class) -> Dict:
    """
    Audit indexes for a single model.
    
    Args:
        model_class: Django model class
    
    Returns:
        Dict with audit results
    """
    model_name = f"{model_class._meta.app_label}.{model_class.__name__}"
    existing_indexes = get_model_indexes(model_class)
    
    # Check for mandatory indexes
    missing_indexes = []
    found_indexes = []
    
    for field_name, index_spec in MANDATORY_INDEXES.items():
        # Check if field exists
        if not hasattr(model_class._meta, 'get_field'):
            continue
        
        try:
            field = model_class._meta.get_field(field_name)
        except:
            # Field doesn't exist, skip
            continue
        
        # Check if indexed
        is_indexed = False
        for idx in existing_indexes:
            if field_name in idx['fields']:
                is_indexed = True
                found_indexes.append({
                    'field': field_name,
                    'index': idx,
                    'spec': index_spec,
                })
                break
        
        if not is_indexed and index_spec['required']:
            missing_indexes.append({
                'field': field_name,
                'spec': index_spec,
            })
    
    return {
        'model': model_name,
        'existing_indexes': existing_indexes,
        'missing_indexes': missing_indexes,
        'found_indexes': found_indexes,
        'status': 'pass' if not missing_indexes else 'fail',
    }


def audit_all_models() -> Dict[str, Dict]:
    """
    Audit indexes for all high-read models.
    
    Returns:
        Dict mapping model names to audit results
    """
    results = {}
    
    for model_path in HIGH_READ_MODELS:
        try:
            app_label, model_name = model_path.split('.')
            model_class = apps.get_model(app_label, model_name)
            results[model_path] = audit_model_indexes(model_class)
        except LookupError:
            # Model not found (app not installed)
            results[model_path] = {
                'model': model_path,
                'status': 'skip',
                'reason': 'Model not found (app not installed)',
            }
        except Exception as e:
            results[model_path] = {
                'model': model_path,
                'status': 'error',
                'error': str(e),
            }
    
    return results


def format_audit_report(results: Dict[str, Dict]) -> str:
    """
    Format audit results as a readable report.
    
    Args:
        results: Audit results from audit_all_models()
    
    Returns:
        Formatted report string
    """
    report = ["📊 INDEX AUDIT REPORT — PART 5 — PRODUCTION READINESS\n"]
    report.append("=" * 70)
    report.append("")
    
    passed = []
    failed = []
    skipped = []
    errors = []
    
    for model_path, result in results.items():
        if result.get('status') == 'pass':
            passed.append(model_path)
        elif result.get('status') == 'fail':
            failed.append(model_path)
        elif result.get('status') == 'skip':
            skipped.append(model_path)
        else:
            errors.append(model_path)
    
    # Summary
    report.append("📋 SUMMARY:")
    report.append(f"  ✅ Passed: {len(passed)}")
    report.append(f"  ❌ Failed: {len(failed)}")
    report.append(f"  ⏭️  Skipped: {len(skipped)}")
    report.append(f"  ⚠️  Errors: {len(errors)}")
    report.append("")
    
    # Failed models
    if failed:
        report.append("❌ MODELS WITH MISSING INDEXES:")
        report.append("")
        for model_path in failed:
            result = results[model_path]
            report.append(f"  📄 {model_path}:")
            for missing in result.get('missing_indexes', []):
                report.append(f"    - Missing: {missing['field']} ({missing['spec']['reason']})")
            report.append("")
    
    # Passed models
    if passed:
        report.append("✅ MODELS WITH ALL REQUIRED INDEXES:")
        for model_path in passed:
            report.append(f"  ✓ {model_path}")
        report.append("")
    
    # Skipped models
    if skipped:
        report.append("⏭️  SKIPPED MODELS (Not Installed):")
        for model_path in skipped:
            report.append(f"  - {model_path}")
        report.append("")
    
    # Recommendations
    if failed:
        report.append("💡 RECOMMENDATIONS:")
        report.append("  1. Add missing indexes via migrations")
        report.append("  2. Use Meta.indexes for composite indexes")
        report.append("  3. Use db_index=True for single-field indexes")
        report.append("  4. Verify with EXPLAIN ANALYZE in production")
        report.append("")
    
    return "\n".join(report)


if __name__ == '__main__':
    """
    Run index audit.
    
    Usage:
        python core/index_audit.py
    
    Exit codes:
        0: All models have required indexes
        1: Some models missing indexes
    """
    import sys
    import django
    from django.conf import settings
    
    # Setup Django
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
        django.setup()
    
    results = audit_all_models()
    report = format_audit_report(results)
    print(report)
    
    # Check if any failed
    has_failures = any(r.get('status') == 'fail' for r in results.values())
    
    if has_failures:
        sys.exit(1)
    else:
        sys.exit(0)




