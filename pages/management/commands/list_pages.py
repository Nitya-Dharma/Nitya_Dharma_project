"""
Django management command to list all pages with their addresses.
"""
from django.core.management.base import BaseCommand
from pages.models import Page


class Command(BaseCommand):
    help = 'List all pages with their addresses'

    def handle(self, *args, **options):
        pages = Page.objects.all().order_by('id')
        total = pages.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No pages found in database.'))
            return
        
        self.stdout.write(f'Total Pages: {total}')
        self.stdout.write('=' * 80)
        
        for i, page in enumerate(pages, 1):
            address = page.address if page.address else '(empty)'
            self.stdout.write(f'\n{i}. {page.title}')
            self.stdout.write(f'   Public ID: {page.public_id}')
            self.stdout.write(f'   Slug: {page.slug}')
            self.stdout.write(f'   Address: {address}')
            self.stdout.write(f'   Status: {page.status}')
        
        self.stdout.write('\n' + '=' * 80)



















