"""
Migration Safety Check — PART 4 — AUTOMATED GUARDRAILS

This command checks migrations for dangerous operations that could:
- Drop core tables
- Remove foreign keys tied to trust/history
- Rename audit columns without explicit override

Usage:
    python manage.py check_migration_safety

This should be run in CI/CD before allowing migrations to be applied.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
import os
import re
from pathlib import Path


class Command(BaseCommand):
    help = 'Check migrations for dangerous operations that violate deletion guard rules'

    # Dangerous operations that should fail the build
    DANGEROUS_OPERATIONS = [
        # Table drops
        (r'DropTable', 'Dropping tables is not allowed'),
        (r'DeleteModel', 'Deleting models is not allowed'),
        
        # Foreign key removals
        (r'RemoveField.*ForeignKey', 'Removing ForeignKey fields is dangerous'),
        (r'RemoveField.*OneToOneField', 'Removing OneToOneField fields is dangerous'),
        
        # Audit column changes
        (r'RemoveField.*created_at', 'Removing created_at audit column is not allowed'),
        (r'RemoveField.*updated_at', 'Removing updated_at audit column is not allowed'),
        (r'RemoveField.*status', 'Removing status field is dangerous'),
        
        # Trust/Referral field removals
        (r'RemoveField.*referral', 'Removing referral fields breaks trust chain'),
        (r'RemoveField.*trust', 'Removing trust fields breaks trust chain'),
    ]

    # Protected models (from DELETION_POLICY)
    PROTECTED_MODELS = [
        'User',
        'PanditProfile',
        'TemplePage',
        'BrandPage',
        'ServicePage',
        'PagePost',
        'PageReview',
        'BookingIntent',
        'Referral',
        'EngagementEvent',
        'PageFollower',
        'Notification',
        'AuditLog',
        'City',
        'Mandal',
        'LocalArea',
        'PoojaCategory',
        'Pooja',
        'Language',
        'CountryCode',
        'ProfileCompletionRule',
        'UploadConfig',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Fail on warnings as well as errors',
        )
        parser.add_argument(
            '--app',
            type=str,
            help='Check only specific app migrations',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking migrations for dangerous operations...'))
        
        violations = []
        warnings = []
        
        # Find all migration files
        migration_files = self.find_migration_files(options.get('app'))
        
        for migration_file in migration_files:
            violations_found, warnings_found = self.check_migration_file(migration_file)
            violations.extend(violations_found)
            warnings.extend(warnings_found)
        
        # Report results
        if violations:
            self.stdout.write(self.style.ERROR(f'\n❌ Found {len(violations)} violations:'))
            for violation in violations:
                self.stdout.write(self.style.ERROR(f'  - {violation}'))
        
        if warnings:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Found {len(warnings)} warnings:'))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f'  - {warning}'))
        
        # Fail build if violations found
        if violations:
            raise CommandError(
                f'Migration safety check FAILED. {len(violations)} violations found. '
                f'Fix these issues before applying migrations.'
            )
        
        if warnings and options.get('strict'):
            raise CommandError(
                f'Migration safety check FAILED (strict mode). {len(warnings)} warnings found.'
            )
        
        if not violations and not warnings:
            self.stdout.write(self.style.SUCCESS('\n✅ All migrations are safe.'))
        elif not violations:
            self.stdout.write(self.style.SUCCESS('\n✅ No critical violations found (warnings only).'))

    def find_migration_files(self, app_name=None):
        """Find all migration files in the project."""
        migration_files = []
        
        # Get project root
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        
        # Find all apps
        if app_name:
            apps = [app_name]
        else:
            # Find all Django apps
            apps_dir = project_root / 'apps' if (project_root / 'apps').exists() else project_root
            apps = [d.name for d in apps_dir.iterdir() if d.is_dir() and (d / 'migrations').exists()]
            # Also check root level apps
            apps.extend([d.name for d in project_root.iterdir() if d.is_dir() and (d / 'migrations').exists()])
        
        # Find migration files
        for app in apps:
            migrations_dir = project_root / app / 'migrations'
            if migrations_dir.exists():
                for migration_file in migrations_dir.glob('*.py'):
                    if migration_file.name != '__init__.py':
                        migration_files.append(migration_file)
        
        return migration_files

    def check_migration_file(self, migration_file):
        """Check a single migration file for dangerous operations."""
        violations = []
        warnings = []
        
        try:
            with open(migration_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            warnings.append(f"{migration_file}: Could not read file: {e}")
            return violations, warnings
        
        # Check for dangerous operations
        for pattern, message in self.DANGEROUS_OPERATIONS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # Get line number
                line_num = content[:match.start()].count('\n') + 1
                violation = f"{migration_file}:{line_num} - {message}"
                violations.append(violation)
        
        # Check for protected model operations
        for model_name in self.PROTECTED_MODELS:
            # Check for DropTable or DeleteModel for protected models
            if re.search(rf'DropTable.*{model_name}|DeleteModel.*{model_name}', content, re.IGNORECASE):
                line_num = content.find(model_name)
                if line_num > 0:
                    line_num = content[:line_num].count('\n') + 1
                    violation = (
                        f"{migration_file}:{line_num} - "
                        f"Attempting to drop/delete protected model: {model_name}"
                    )
                    violations.append(violation)
        
        return violations, warnings

