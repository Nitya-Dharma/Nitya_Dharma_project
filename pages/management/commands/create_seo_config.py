"""
Management command to create initial SiteSEOConfig.
Run this command to set up global SEO configuration.

Usage:
    python manage.py create_seo_config
"""
from django.core.management.base import BaseCommand
from pages.models_cms import SiteSEOConfig


class Command(BaseCommand):
    help = 'Create or update SiteSEOConfig with default values'

    def handle(self, *args, **options):
        config, created = SiteSEOConfig.objects.get_or_create(
            pk=1,
            defaults={
                'organization_name': 'Nitya Dharma',
                'twitter_handle': '',
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS('SUCCESS: Created SiteSEOConfig with default values')
            )
        else:
            self.stdout.write(
                self.style.WARNING('NOTE: SiteSEOConfig already exists (pk=1)')
            )

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'SiteSEOConfig Status:\n'
                f'  Organization Name: {config.organization_name}\n'
                f'  Twitter Handle: {config.twitter_handle or "(not set)"}\n'
                f'  Organization Logo: {"Set" if config.organization_logo else "Not set"}\n'
                f'  Default OG Image: {"Set" if config.default_og_image else "Not set"}\n\n'
                f'To configure:\n'
                f'  Visit: /nd-control-panel/pages/siteseoconfig/\n'
                f'  Upload organization logo and default OG image (1200x630 recommended)'
            )
        )

