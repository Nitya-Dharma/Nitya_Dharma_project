"""
Management command to create PanditProfile for existing Pandit users who don't have one.

This ensures all Pandits have profiles so dashboard links work correctly.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User
from profiles.models import PanditProfile


class Command(BaseCommand):
    help = 'Create PanditProfile for existing Pandit users who do not have one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating profiles',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find all Pandit users without profiles
        pandit_users = User.objects.filter(role='pandit')
        users_without_profiles = []
        
        for user in pandit_users:
            if not hasattr(user, 'pandit_profile'):
                users_without_profiles.append(user)
        
        if not users_without_profiles:
            self.stdout.write(
                self.style.SUCCESS('All Pandit users already have profiles.')
            )
            return
        
        self.stdout.write(
            f'Found {len(users_without_profiles)} Pandit users without profiles:'
        )
        for user in users_without_profiles:
            self.stdout.write(f'  - {user.email} (ID: {user.id})')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\nDRY RUN: No profiles will be created.')
            )
            return
        
        # Create profiles
        created_count = 0
        with transaction.atomic():
            for user in users_without_profiles:
                try:
                    PanditProfile.objects.create(user=user)
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Created profile for {user.email}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to create profile for {user.email}: {str(e)}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} PanditProfile(s).'
            )
        )












