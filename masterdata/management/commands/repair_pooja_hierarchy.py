"""
Management command to repair Pooja → PoojaCategory hierarchy.

- Lists poojas without pooja_category (broken hierarchy).
- Optionally fixes by assigning category from legacy `category` field
  (maps to PoojaCategory by display name) or by --category-id.

Usage:
  python manage.py repair_pooja_hierarchy
      -> list poojas without pooja_category
  python manage.py repair_pooja_hierarchy --fix
      -> assign pooja_category from legacy category where possible
  python manage.py repair_pooja_hierarchy --fix --dry-run
      -> show what would be updated
  python manage.py repair_pooja_hierarchy --fix-id <pooja_id> --category-id <category_id>
      -> set category for one pooja
"""
from django.core.management.base import BaseCommand
from django.db import transaction, models
from masterdata.models import Pooja, PoojaCategory


class Command(BaseCommand):
    help = 'List and optionally repair poojas without pooja_category (Pooja Category → Pooja hierarchy)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Assign pooja_category from legacy category field where possible',
        )
        parser.add_argument(
            '--fix-id',
            type=int,
            metavar='ID',
            help='Pooja ID to set category for',
        )
        parser.add_argument(
            '--category-id',
            type=int,
            metavar='ID',
            help='PoojaCategory ID to assign (required with --fix-id)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be changed',
        )

    def handle(self, *args, **options):
        fix_bulk = options.get('fix')
        fix_id = options.get('fix_id')
        category_id = options.get('category_id')
        dry_run = options.get('dry_run')

        # Single pooja fix: --fix-id N --category-id M
        if fix_id is not None:
            if category_id is None:
                self.stderr.write(self.style.ERROR('--category-id is required when using --fix-id'))
                return
            try:
                pooja = Pooja.objects.get(pk=fix_id)
            except Pooja.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Pooja with id={fix_id} not found.'))
                return
            try:
                category = PoojaCategory.objects.get(pk=category_id)
            except PoojaCategory.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'PoojaCategory with id={category_id} not found.'))
                return
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f'[DRY-RUN] Would set pooja "{pooja.name}" (id={pooja.id}) to category "{category.name}" (id={category.id})'))
                return
            pooja.pooja_category = category
            pooja.save(update_fields=['pooja_category'])
            self.stdout.write(self.style.SUCCESS(f'Set category "{category.name}" for pooja "{pooja.name}" (id={pooja.id})'))
            return

        # List poojas without category
        broken = list(
            Pooja.objects.filter(
                models.Q(pooja_category__isnull=True) | models.Q(pooja_category_id=0)
            ).order_by('name')
        )

        self.stdout.write('--- Poojas without PoojaCategory ---')
        if not broken:
            self.stdout.write(self.style.SUCCESS('None. All poojas have a category set.'))
            return

        for p in broken:
            legacy = f' (legacy category: {p.get_category_display()})' if p.category else ' (no legacy category)'
            self.stdout.write(f'  id={p.id}  name="{p.name}"{legacy}')
        self.stdout.write(f'Total: {len(broken)}.')

        if not fix_bulk:
            self.stdout.write('Run with --fix to assign pooja_category from legacy category where possible.')
            return

        # Build mapping: legacy display name -> PoojaCategory.
        # Legacy display is e.g. "A. Daily & Common Household Poojas"; DB may store with or without "A. " prefix.
        name_to_category = {}
        for cat in PoojaCategory.objects.all():
            name_to_category[cat.name] = cat
            # Map legacy display (with "X. " prefix) to this category if cat.name matches suffix
            if len(cat.name) > 0:
                for _code, display in Pooja.CATEGORY_CHOICES:
                    if display not in name_to_category and (
                        cat.name == display or (len(display) > 3 and display[1:3] == '. ' and cat.name == display[3:].strip())
                    ):
                        name_to_category[display] = cat
                        break
        # Ensure every legacy choice has a mapping if any category name matches (with or without prefix)
        for _code, display in Pooja.CATEGORY_CHOICES:
            if display in name_to_category:
                continue
            suffix = display[3:].strip() if len(display) > 3 and display[1:3] == '. ' else display
            for cat in PoojaCategory.objects.all():
                if cat.name == display or cat.name == suffix:
                    name_to_category[display] = cat
                    break

        if not any(display in name_to_category for _code, display in Pooja.CATEGORY_CHOICES):
            self.stdout.write(
                self.style.WARNING(
                    'No PoojaCategory names match legacy labels (e.g. "A. Daily & Common Household Poojas" or "Daily & Common Household Poojas"). '
                    'Create categories in Master Data or ensure names match.'
                )
            )

        updated = 0
        skipped = 0
        for pooja in broken:
            target_category = None
            if pooja.category:
                display = pooja.get_category_display()
                target_category = name_to_category.get(display)
            if not target_category:
                skipped += 1
                self.stdout.write(self.style.WARNING(f'  Skip id={pooja.id} "{pooja.name}": no matching PoojaCategory'))
                continue
            if dry_run:
                self.stdout.write(self.style.SUCCESS(f'  [DRY-RUN] Would set id={pooja.id} "{pooja.name}" -> "{target_category.name}"'))
                updated += 1
                continue
            with transaction.atomic():
                pooja.pooja_category = target_category
                pooja.save(update_fields=['pooja_category'])
                updated += 1
                self.stdout.write(self.style.SUCCESS(f'  Set id={pooja.id} "{pooja.name}" -> "{target_category.name}"'))

        self.stdout.write(f'Updated: {updated}, Skipped: {skipped}.')