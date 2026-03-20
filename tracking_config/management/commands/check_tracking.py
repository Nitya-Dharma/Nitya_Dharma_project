"""
Management command to check tracking configuration status.
"""
from django.core.management.base import BaseCommand
from tracking_config.models import TrackingConfiguration


class Command(BaseCommand):
    help = 'Check tracking configuration status'

    def handle(self, *args, **options):
        # Check for active configuration
        active_config = TrackingConfiguration.objects.filter(is_active=True).first()
        
        if not active_config:
            self.stdout.write(
                self.style.ERROR('ERROR: No active tracking configuration found!')
            )
            self.stdout.write(
                self.style.WARNING('\nTo fix this:')
            )
            self.stdout.write('1. Log in as Super Admin')
            self.stdout.write('2. Go to /nd-control-panel/tracking_config/trackingconfiguration/')
            self.stdout.write('3. Create a new TrackingConfiguration')
            self.stdout.write('4. Set "Is Active" to True')
            self.stdout.write('5. Add your GTM snippets in Head, Body, and Footer fields')
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'SUCCESS: Active tracking configuration found: {active_config}')
        )
        self.stdout.write(f'   Provider: {active_config.get_provider_type_display()}')
        self.stdout.write(f'   Created by: {active_config.created_by.email}')
        self.stdout.write(f'   Created at: {active_config.created_at}')
        
        # Check snippets
        has_head = bool(active_config.head_snippet and active_config.head_snippet.strip())
        has_body = bool(active_config.body_snippet and active_config.body_snippet.strip())
        has_footer = bool(active_config.footer_snippet and active_config.footer_snippet.strip())
        
        self.stdout.write('\nSnippet Status:')
        self.stdout.write(f'   Head Snippet: {"[PRESENT]" if has_head else "[EMPTY]"}')
        self.stdout.write(f'   Body Snippet: {"[PRESENT]" if has_body else "[EMPTY]"}')
        self.stdout.write(f'   Footer Snippet: {"[PRESENT]" if has_footer else "[EMPTY]"}')
        
        if not (has_head or has_body or has_footer):
            self.stdout.write(
                self.style.WARNING('\nWARNING: All snippets are empty! Add GTM code in Django Admin.')
            )
        
        # Check excluded routes
        excluded = active_config.get_excluded_patterns_list()
        if excluded:
            self.stdout.write(f'\nExcluded Routes: {", ".join(excluded)}')
        else:
            self.stdout.write('\nExcluded Routes: None (using default exclusions)')
        
        self.stdout.write('\nSUCCESS: Configuration looks good! GTM code should appear on public pages.')

