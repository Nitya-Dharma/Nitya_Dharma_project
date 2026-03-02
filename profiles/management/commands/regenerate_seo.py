"""
Management command to regenerate SEO metadata for Pandit Profiles.
"""
from django.core.management.base import BaseCommand
from profiles.models import PanditProfile
from profiles.seo_services import auto_generate_pandit_seo


class Command(BaseCommand):
    help = 'Regenerate SEO metadata for Pandit Profiles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Regenerate SEO for all profiles',
        )
        parser.add_argument(
            '--public-id',
            type=str,
            help='Regenerate SEO for a specific profile (by public_id)',
        )

    def handle(self, *args, **options):
        if options['public_id']:
            # Regenerate for specific profile
            try:
                profile = PanditProfile.objects.get(public_id=options['public_id'])
                if auto_generate_pandit_seo(profile, force=True):
                    profile.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Regenerated SEO for {profile.get_display_name()} ({profile.user.email})')
                    )
                    self.stdout.write(f'  Title: {profile.seo_title}')
                    self.stdout.write(f'  Description: {profile.seo_description[:60]}...' if profile.seo_description else '  Description: (empty)')
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Could not regenerate SEO for {profile.get_display_name()}')
                    )
            except PanditProfile.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Profile with public_id {options["public_id"]} not found')
                )
        elif options['all']:
            # Regenerate for all profiles
            profiles = PanditProfile.objects.all()
            updated_count = 0
            
            for profile in profiles:
                if auto_generate_pandit_seo(profile, force=True):
                    profile.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Regenerated SEO for {profile.get_display_name()} ({profile.user.email})')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'\nRegenerated SEO metadata for {updated_count} profile(s)')
            )
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --all or --public-id <public_id>')
            )

