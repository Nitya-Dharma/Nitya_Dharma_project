"""
Management command to repair location hierarchy: cities without state, areas without city.

Use after fixing the profile edit flow so new cities always get a state.
- Lists cities with state NULL or blank.
- Optionally fix by setting state on a city (by id or name).

Usage:
  python manage.py repair_location_hierarchy
      -> list cities without state (and areas without city if any)
  python manage.py repair_location_hierarchy --fix-id 123 --state "Maharashtra"
      -> set state for city id=123
  python manage.py repair_location_hierarchy --fix-name "Pune" --state "Maharashtra"
      -> set state for city named Pune (case-insensitive)
"""
from django.core.management.base import BaseCommand
from django.db import transaction, models
from masterdata.models import City, LocalArea


class Command(BaseCommand):
    help = 'List and optionally repair cities without state; list areas without city'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-id',
            type=int,
            metavar='ID',
            help='City ID to set state for',
        )
        parser.add_argument(
            '--fix-name',
            type=str,
            metavar='NAME',
            help='City name to set state for (case-insensitive)',
        )
        parser.add_argument(
            '--state',
            type=str,
            required=False,
            metavar='STATE',
            help='State name to set (required with --fix-id or --fix-name)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be changed',
        )

    def handle(self, *args, **options):
        fix_id = options.get('fix_id')
        fix_name = options.get('fix_name')
        state_value = (options.get('state') or '').strip()
        dry_run = options.get('dry_run', False)

        if fix_id or fix_name:
            if not state_value:
                self.stderr.write(self.style.ERROR('--state is required when using --fix-id or --fix-name'))
                return
            with transaction.atomic():
                if fix_id:
                    city = City.objects.filter(id=fix_id).first()
                    if not city:
                        self.stderr.write(self.style.ERROR(f'City with id={fix_id} not found.'))
                        return
                    label = f'id={fix_id} ({city.name})'
                else:
                    city = City.objects.filter(name__iexact=fix_name.strip()).first()
                    if not city:
                        self.stderr.write(self.style.ERROR(f'City named "{fix_name}" not found.'))
                        return
                    label = f'"{city.name}" (id={city.id})'
                if (city.state or '').strip() == state_value:
                    self.stdout.write(self.style.WARNING(f'City {label} already has state="{state_value}".'))
                    return
                if dry_run:
                    self.stdout.write(self.style.SUCCESS(f'[DRY-RUN] Would set state="{state_value}" for city {label}'))
                    return
                city.state = state_value
                city.save(update_fields=['state'])
                self.stdout.write(self.style.SUCCESS(f'Set state="{state_value}" for city {label}'))
            return

        # List mode
        cities_without_state = list(
            City.objects.filter(models.Q(state__isnull=True) | models.Q(state='')).order_by('name')
        )
        areas_without_city = list(LocalArea.objects.filter(city__isnull=True).order_by('name'))

        self.stdout.write('--- Cities without state ---')
        if not cities_without_state:
            self.stdout.write(self.style.SUCCESS('None. All cities have a state set.'))
        else:
            for c in cities_without_state:
                self.stdout.write(f'  id={c.id}  name="{c.name}"')
            self.stdout.write(f'Total: {len(cities_without_state)}. Fix with: --fix-id <id> --state "StateName" or --fix-name "CityName" --state "StateName"')

        self.stdout.write('--- Areas without city (schema expects none) ---')
        if not areas_without_city:
            self.stdout.write(self.style.SUCCESS('None.'))
        else:
            for a in areas_without_city:
                self.stdout.write(f'  id={a.id}  name="{a.name}"')
            self.stdout.write(f'Total: {len(areas_without_city)}. Fix manually in DB or add a repair step.')