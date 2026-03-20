"""
Management command to initialize WordPress-style CMS pages.
Creates draft pages for About Us, Terms, and Privacy Policy if they don't exist.
Super Admin should edit and publish these pages from Django admin.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from pages.models_cms import CMSPage, SiteSEOConfig

User = get_user_model()


class Command(BaseCommand):
    help = 'Initialize WordPress-style CMS pages (draft mode)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Initializing WordPress-Style CMS Pages ===\n'))

        # Get or create a superuser for created_by/updated_by
        superuser = User.objects.filter(is_superuser=True).first()
        if not superuser:
            self.stdout.write(self.style.ERROR('ERROR: No superuser found. Please create a superuser first.'))
            return

        # Initialize SiteSEOConfig if it doesn't exist
        seo_config, created = SiteSEOConfig.objects.get_or_create(
            pk=1,
            defaults={
                'organization_name': 'Nitya Dharma',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created SiteSEOConfig'))
        else:
            self.stdout.write(self.style.WARNING('  SiteSEOConfig already exists'))

        # Define initial pages
        initial_pages = [
            {
                'page_type': 'about',
                'title': 'About Nitya Dharma',
                'slug': 'about-us',
                'content': '<h2>Our Mission</h2><p>Nitya Dharma is India\'s premier digital platform connecting devotees with verified and trusted pandits for authentic religious ceremonies, poojas, and spiritual services.</p><h2>What We Offer</h2><p>We provide a transparent, secure platform where users can discover, verify, and book qualified pandits for their spiritual needs.</p><h2>Why Choose Us</h2><p>All pandits on our platform are verified, ensuring quality, authenticity, and cultural respect in every service.</p>',
                'seo_title': 'About Nitya Dharma | Verified Pandit Platform',
                'seo_description': 'Learn about Nitya Dharma, a trusted platform connecting devotees with verified pandits and temples across India.',
                'seo_keywords': 'about nitya dharma, pandit platform, religious ceremonies, pooja services',
            },
            {
                'page_type': 'terms',
                'title': 'Terms and Conditions',
                'slug': 'terms-and-conditions',
                'content': '<h2>User Responsibilities</h2><p>Users must provide accurate information and use the platform responsibly.</p><h2>Pandit Responsibilities</h2><p>Pandits must maintain accurate profiles and deliver services as described.</p><h2>Platform Limitations</h2><p>Nitya Dharma is a platform connecting users and pandits. We are not responsible for the quality of services provided by individual pandits.</p><h2>Content Policy</h2><p>All content must be respectful and comply with our community guidelines.</p><h2>Liability</h2><p>Users and pandits are responsible for their own interactions and agreements.</p><h2>Governing Law</h2><p>These terms are governed by Indian law.</p>',
                'seo_title': 'Terms and Conditions - Nitya Dharma',
                'seo_description': 'Read Nitya Dharma\'s Terms and Conditions. Understand user responsibilities, platform policies, and governing laws.',
                'seo_keywords': 'terms and conditions, user agreement, platform terms',
            },
            {
                'page_type': 'privacy',
                'title': 'Privacy Policy',
                'slug': 'privacy-policy',
                'content': '<h2>Information We Collect</h2><p>We collect information you provide, such as name, email, phone number, and service preferences.</p><h2>How We Use Information</h2><p>We use your information to provide services, improve our platform, and communicate with you.</p><h2>Data Security</h2><p>We implement security measures to protect your personal information.</p><h2>Cookies</h2><p>We use cookies to enhance your experience and analyze platform usage.</p><h2>Third-Party Services</h2><p>We may use third-party services that have their own privacy policies.</p><h2>User Rights</h2><p>You have the right to access, update, or delete your personal information.</p><h2>Contact Information</h2><p>For privacy concerns, please contact us through our contact form.</p>',
                'seo_title': 'Privacy Policy - Nitya Dharma | Data Protection',
                'seo_description': 'Nitya Dharma Privacy Policy. Learn how we collect, use, and protect your personal information. Understand your privacy rights.',
                'seo_keywords': 'privacy policy, data protection, privacy rights',
            },
        ]

        # Create pages if they don't exist
        created_count = 0
        for page_data in initial_pages:
            page_type = page_data.pop('page_type')
            page, created = CMSPage.objects.get_or_create(
                page_type=page_type,
                defaults={
                    **page_data,
                    'created_by': superuser,
                    'updated_by': superuser,
                    'is_published': False,  # Draft mode - Super Admin must publish
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created {page.get_page_type_display()} page (DRAFT)'))
            else:
                self.stdout.write(self.style.WARNING(f'  {page.get_page_type_display()} page already exists'))

        self.stdout.write(self.style.SUCCESS(f'\n=== Initialization Complete ==='))
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} new pages'))
        self.stdout.write(self.style.WARNING('\n⚠ IMPORTANT: All pages are in DRAFT mode.'))
        self.stdout.write(self.style.WARNING('  1. Go to /nd-control-panel/pages/cmspage/'))
        self.stdout.write(self.style.WARNING('  2. Edit each page and refine content'))
        self.stdout.write(self.style.WARNING('  3. Set is_published=True when ready to publish'))
        self.stdout.write(self.style.WARNING('  4. Configure SiteSEOConfig at /nd-control-panel/pages/siteseoconfig/'))










