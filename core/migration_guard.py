"""
Migration Guard — PART 4 — AUTOMATED GUARDRAILS

TASK 4.4: Migration Guard

This module provides CI/CD checks to prevent dangerous migrations.

RULES:
- No migration may:
  - Drop core tables
  - Remove foreign keys tied to trust/history
  - Rename audit columns without explicit override
  - Use CASCADE delete for historical data

ACTION:
- If migration violates rule → FAIL BUILD
"""

import re
import os
from pathlib import Path
from typing import List, Tuple, Dict


# Protected tables that must never be dropped
PROTECTED_TABLES = [
    'accounts_user',
    'profiles_panditprofile',
    'pages_templepage',
    'pages_brandpage',
    'pages_servicepage',
    'pages_pagepost',
    'reviews_review',
    'booking_intent_bookingintent',
    'referrals_referral',
    'engagement_engagementevent',
    'notifications_notification',
    'core_auditlog',
    'masterdata_city',
    'masterdata_mandal',
    'masterdata_localarea',
    'masterdata_poojacategory',
    'masterdata_pooja',
    'masterdata_language',
    'masterdata_countrycode',
]

# Protected columns that must never be removed
PROTECTED_COLUMNS = [
    'id',
    'public_id',
    'status',
    'created_at',
    'updated_at',
    'user_id',
    'referred_by_id',
    'actor_id',
    'target_entity_id',
]

# Dangerous operations that should fail the build
DANGEROUS_OPERATIONS = [
    r'DropTable',
    r'DeleteModel',
    r'RemoveField',
    r'AlterField.*on_delete.*CASCADE',  # Should be PROTECT for historical data
    r'RenameField.*status',  # Status field should not be renamed
    r'RenameField.*created_at',  # Timestamps should not be renamed
    r'RenameField.*updated_at',
]


def scan_migration_file(file_path: Path) -> List[Tuple[str, int, str]]:
    """
    Scan a migration file for dangerous operations.
    
    Args:
        file_path: Path to migration file
    
    Returns:
        List of (operation, line_number, context) tuples
    """
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Check for dangerous operations
                for pattern in DANGEROUS_OPERATIONS:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append((
                            pattern,
                            line_num,
                            line.strip()
                        ))
                
                # Check for dropping protected tables
                if 'DropTable' in line or 'DeleteModel' in line:
                    for table in PROTECTED_TABLES:
                        if table.lower() in line.lower():
                            violations.append((
                                f"Dropping protected table: {table}",
                                line_num,
                                line.strip()
                            ))
                
                # Check for removing protected columns
                if 'RemoveField' in line:
                    for column in PROTECTED_COLUMNS:
                        if column.lower() in line.lower():
                            violations.append((
                                f"Removing protected column: {column}",
                                line_num,
                                line.strip()
                            ))
    
    except Exception as e:
        violations.append((
            f"Error reading migration file: {e}",
            0,
            str(file_path)
        ))
    
    return violations


def scan_all_migrations(migrations_dir: Path) -> Dict[str, List[Tuple[str, int, str]]]:
    """
    Scan all migration files in a directory.
    
    Args:
        migrations_dir: Path to migrations directory
    
    Returns:
        Dict mapping file paths to violations
    """
    violations_by_file = {}
    
    if not migrations_dir.exists():
        return violations_by_file
    
    for migration_file in migrations_dir.glob('*.py'):
        if migration_file.name == '__init__.py':
            continue
        
        violations = scan_migration_file(migration_file)
        if violations:
            violations_by_file[str(migration_file)] = violations
    
    return violations_by_file


def check_migrations(base_dir: Path = None) -> Tuple[bool, Dict[str, List[Tuple[str, int, str]]]]:
    """
    Check all migrations for dangerous operations.
    
    Args:
        base_dir: Base directory of Django project (default: current directory)
    
    Returns:
        Tuple of (is_safe: bool, violations_by_file: dict)
    """
    if base_dir is None:
        base_dir = Path.cwd()
    
    violations_by_file = {}
    
    # Find all apps with migrations
    for app_dir in base_dir.iterdir():
        if app_dir.is_dir() and (app_dir / 'migrations').exists():
            migrations_dir = app_dir / 'migrations'
            violations = scan_all_migrations(migrations_dir)
            violations_by_file.update(violations)
    
    is_safe = len(violations_by_file) == 0
    
    return is_safe, violations_by_file


def format_violations_report(violations_by_file: Dict[str, List[Tuple[str, int, str]]]) -> str:
    """
    Format violations as a readable report.
    
    Args:
        violations_by_file: Dict of violations by file
    
    Returns:
        Formatted report string
    """
    if not violations_by_file:
        return "✅ No dangerous migrations found."
    
    report = ["❌ DANGEROUS MIGRATIONS DETECTED:\n"]
    
    for file_path, violations in violations_by_file.items():
        report.append(f"\n📄 {file_path}:")
        for pattern, line_num, context in violations:
            report.append(f"  Line {line_num}: {pattern}")
            report.append(f"    Context: {context}")
    
    report.append("\n\n🚫 BUILD SHOULD FAIL")
    report.append("These migrations violate deletion guard rules.")
    
    return "\n".join(report)


if __name__ == '__main__':
    """
    Run migration guard check.
    
    Usage:
        python core/migration_guard.py
    
    Exit codes:
        0: All migrations are safe
        1: Dangerous migrations found
    """
    import sys
    
    is_safe, violations = check_migrations()
    
    if is_safe:
        print("✅ All migrations are safe.")
        sys.exit(0)
    else:
        report = format_violations_report(violations)
        print(report)
        sys.exit(1)




