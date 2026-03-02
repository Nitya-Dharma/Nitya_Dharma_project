"""
Django management command to list all page URLs.
"""
from django.core.management.base import BaseCommand
from pages.models import Page


class Command(BaseCommand):
    help = 'List all page URLs for direct access'

    def handle(self, *args, **options):
        pages = Page.objects.all().order_by('id')
        total = pages.count()
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No pages found in database.'))
            return
        
        # Use localhost for development (change to your domain in production)
        domain = 'localhost:8000'
        protocol = 'http://'  # Use https:// in production
        
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'PAGE DIRECT ACCESS URLs ({total} pages)'))
        self.stdout.write('=' * 80)
        self.stdout.write()
        
        for i, page in enumerate(pages, 1):
            url = f'{protocol}{domain}/pages/{page.public_id}/'
            self.stdout.write(f'{i}. {page.title}')
            self.stdout.write(f'   URL: {url}')
            self.stdout.write(f'   Type: {page.get_page_type_display()} | Status: {page.get_status_display()}')
            if page.cover_image:
                self.stdout.write(f'   Cover Image: Yes')
            if page.profile_image:
                self.stdout.write(f'   Profile Image: Yes')
            self.stdout.write()
        
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'Total: {total} page(s)'))
        self.stdout.write('=' * 80)

