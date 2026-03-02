"""
Management command to backfill public_id for existing PanditProfile records.

This ensures all profiles have a public_id for proper URL generation.
"""
from django.core.management.base import BaseCommand
from profiles.models import PanditProfile
from core.public_id import generate_public_id


class Command(BaseCommand):
    help = 'Backfill public_id for existing PanditProfile records that are missing it'

    def handle(self, *args, **options):
        # Find all profiles without public_id
        profiles_without_id = PanditProfile.objects.filter(public_id__isnull=True)
        count = profiles_without_id.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('All profiles already have public_id. No action needed.'))
            return
        
        self.stdout.write(f'Found {count} profile(s) without public_id. Generating...')
        
        updated = 0
        for profile in profiles_without_id:
            try:
                profile.public_id = generate_public_id()
                profile.save(update_fields=['public_id'])
                updated += 1
                self.stdout.write(f'  - Generated public_id for profile ID {profile.id} (User: {profile.user.email})')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  - Error updating profile ID {profile.id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully updated {updated} profile(s) with public_id.')
        )












