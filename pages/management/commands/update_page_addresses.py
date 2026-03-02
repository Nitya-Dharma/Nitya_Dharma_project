"""
Django management command to update addresses for all pages.
"""
from django.core.management.base import BaseCommand
from pages.models import Page


class Command(BaseCommand):
    help = 'Update addresses for all pages'

    def handle(self, *args, **options):
        pages = Page.objects.all()
        total = pages.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No pages found in database.'))
            return
        
        self.stdout.write(f'Found {total} page(s) to update.')
        self.stdout.write('=' * 60)
        
        updated_count = 0
        
        for page in pages:
            # Update all addresses to "uppal"
            new_address = 'Uppal, Hyderabad, Telangana, India'
            
            # Update if address is different or empty
            if page.address != new_address:
                old_address = page.address or '(empty)'
                page.address = new_address
                page.save(update_fields=['address'])
                updated_count += 1
                
                self.stdout.write(f'\nUpdated: {page.title}')
                self.stdout.write(f'  Old Address: {old_address}')
                self.stdout.write(f'  New Address: {new_address}')
                self.stdout.write(f'  Public ID: {page.public_id}')
            else:
                self.stdout.write(f'\nSkipped (already correct): {page.title}')
                self.stdout.write(f'  Address: {page.address}')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'SUCCESS: Updated {updated_count} out of {total} page(s).'))
        self.stdout.write('=' * 60)

