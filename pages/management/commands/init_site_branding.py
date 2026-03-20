"""
Management command to initialize SiteBranding.
Creates the singleton SiteBranding instance if it doesn't exist.
Super Admin should then upload logos and configure branding from Django admin.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pages.models_cms import SiteBranding

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize SiteBranding singleton instance'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Initializing Site Branding ===\n'))

        # Get or create a superuser for created_by/updated_by
        superuser = User.objects.filter(is_superuser=True).first()
        if not superuser:
            self.stdout.write(self.style.ERROR('ERROR: No superuser found. Please create a superuser first.'))
            return

        # Create SiteBranding if it doesn't exist (singleton pattern)
        branding, created = SiteBranding.objects.get_or_create(
            pk=1,
            defaults={
                'site_name': 'Nitya Dharma',
                'created_by': superuser,
                'updated_by': superuser,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('SUCCESS: Created SiteBranding instance'))
            self.stdout.write(self.style.WARNING('\nNOTE: Next Steps:'))
            self.stdout.write(self.style.WARNING('  1. Go to /nd-control-panel/pages/sitebranding/'))
            self.stdout.write(self.style.WARNING('  2. Upload primary_logo (recommended: 200x200px or larger)'))
            self.stdout.write(self.style.WARNING('  3. Upload secondary_logo (optional, for light/dark mode)'))
            self.stdout.write(self.style.WARNING('  4. Upload favicon (recommended: 16x16 or 32x32)'))
            self.stdout.write(self.style.WARNING('  5. Update site_name if needed'))
        else:
            self.stdout.write(self.style.WARNING('  SiteBranding already exists (pk=1)'))
            self.stdout.write(self.style.SUCCESS('\nSUCCESS: SiteBranding is ready'))
            self.stdout.write(self.style.SUCCESS('  Edit at: /nd-control-panel/pages/sitebranding/'))

