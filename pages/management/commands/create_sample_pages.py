"""
Django management command to create 2 sample temple pages.
"""
from django.core.management.base import BaseCommand
from accounts.models import User
from pages.services import create_page
from pages.constants import PAGE_TYPE_TEMPLE


class Command(BaseCommand):
    help = 'Create 2 sample temple pages for testing'

    def handle(self, *args, **options):
        # Get admin user
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.filter(role='admin').first()
        
        if not admin:
            self.stdout.write(self.style.ERROR('No admin user found. Please create an admin user first.'))
            return
        
        self.stdout.write(f'Using user: {admin.email}')
        self.stdout.write('=' * 60)
        
        # Page 1
        self.stdout.write('\nCreating Sample Temple Page 1...')
        try:
            page1 = create_page(
                user=admin,
                page_type=PAGE_TYPE_TEMPLE,
                payload={
                    'title': 'Shri Hanuman Temple - LB Nagar',
                    'description': 'A sacred temple dedicated to Lord Hanuman, located in LB Nagar, Hyderabad. This temple is known for its peaceful atmosphere and regular puja ceremonies. Devotees visit daily for darshan and blessings.',
                    'address': 'LB Nagar, Hyderabad, Telangana 500074, Near Metro Station'
                }
            )
            self.stdout.write(self.style.SUCCESS('Page 1 created successfully!'))
            self.stdout.write(f'  Title: {page1.title}')
            self.stdout.write(f'  Public ID: {page1.public_id}')
            self.stdout.write(f'  Slug: {page1.slug}')
            self.stdout.write(f'  Status: {page1.status}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Failed to create Page 1: {str(e)}'))
            import traceback
            traceback.print_exc()
            return
        
        # Page 2
        self.stdout.write('\nCreating Sample Temple Page 2...')
        try:
            page2 = create_page(
                user=admin,
                page_type=PAGE_TYPE_TEMPLE,
                payload={
                    'title': 'Sri Venkateswara Swamy Temple - Secunderabad',
                    'description': 'Ancient temple dedicated to Lord Venkateswara, situated in the heart of Secunderabad. This temple attracts devotees from all over the city for daily darshan. The temple conducts special pujas on Fridays and during festivals.',
                    'address': 'Secunderabad, Hyderabad, Telangana 500003'
                }
            )
            self.stdout.write(self.style.SUCCESS('Page 2 created successfully!'))
            self.stdout.write(f'  Title: {page2.title}')
            self.stdout.write(f'  Public ID: {page2.public_id}')
            self.stdout.write(f'  Slug: {page2.slug}')
            self.stdout.write(f'  Status: {page2.status}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'X Failed to create Page 2: {str(e)}'))
            import traceback
            traceback.print_exc()
            return
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('SUCCESS: Both sample temple pages created successfully!'))
        self.stdout.write('=' * 60)

