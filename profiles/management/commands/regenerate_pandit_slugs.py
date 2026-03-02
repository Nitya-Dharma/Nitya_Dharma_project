"""
Management command to regenerate SEO-optimized slugs for existing Pandit profiles.

Usage:
    python manage.py regenerate_pandit_slugs
    
This command will:
- Generate SEO slugs for all Pandit profiles that don't have slugs
- Preserve existing custom slugs
- Ensure all slugs are unique
"""
from django.core.management.base import BaseCommand
from profiles.models import PanditProfile
from core.utils.slug_utils import generate_pandit_slug


class Command(BaseCommand):
    help = 'Regenerate SEO-optimized slugs for existing Pandit profiles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of all slugs (including existing ones)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually updating',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        
        profiles = PanditProfile.objects.all()
        updated_count = 0
        skipped_count = 0
        
        self.stdout.write(self.style.SUCCESS(f'Processing {profiles.count()} Pandit profiles...'))
        
        for profile in profiles:
            # Skip if slug exists and not forcing
            if profile.slug and profile.slug.strip() and not force:
                skipped_count += 1
                continue
            
            # Generate new slug
            base_slug = generate_pandit_slug(profile)
            new_slug = profile.ensure_unique_slug(base_slug)
            
            if dry_run:
                self.stdout.write(
                    f'Would update: {profile.user.get_full_name()} '
                    f'(ID: {profile.id}) -> {new_slug}'
                )
            else:
                old_slug = profile.slug or '(empty)'
                profile.slug = new_slug
                profile.save(update_fields=['slug'])
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated: {profile.user.get_full_name()} '
                        f'({old_slug} -> {new_slug})'
                    )
                )
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN: Would update {updated_count} profiles'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nCompleted: Updated {updated_count} profiles, '
                    f'skipped {skipped_count} profiles'
                )
            )



