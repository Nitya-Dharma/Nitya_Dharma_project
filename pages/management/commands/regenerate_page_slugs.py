"""
Management command to regenerate SEO-optimized slugs for existing Temple pages.

Usage:
    python manage.py regenerate_page_slugs
    
This command will:
- Generate SEO slugs for all pages that don't have slugs
- Preserve existing custom slugs
- Ensure all slugs are unique per page_type
"""
from django.core.management.base import BaseCommand
from pages.models import Page
from core.utils.slug_utils import generate_temple_slug


class Command(BaseCommand):
    help = 'Regenerate SEO-optimized slugs for existing Temple pages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of all slugs (including existing ones)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually updating',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        
        pages = Page.objects.all()
        updated_count = 0
        skipped_count = 0
        
        self.stdout.write(self.style.SUCCESS(f'Processing {pages.count()} pages...'))
        
        for page in pages:
            # Skip if slug exists and not forcing
            if page.slug and page.slug.strip() and not force:
                skipped_count += 1
                continue
            
            # Skip if page has followers (slug is locked)
            if page.followers_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipped (has {page.followers_count} followers): {page.name} '
                        f'(slug locked: {page.slug})'
                    )
                )
                skipped_count += 1
                continue
            
            # Generate new slug
            base_slug = generate_temple_slug(page)
            
            # Ensure uniqueness per page_type
            new_slug = base_slug
            counter = 1
            while Page.objects.filter(page_type=page.page_type, slug=new_slug).exclude(pk=page.pk).exists():
                suffix = f"-{counter}"
                if len(base_slug) + len(suffix) > 255:
                    available_length = 255 - len(suffix)
                    new_slug = base_slug[:available_length] + suffix
                else:
                    new_slug = base_slug + suffix
                counter += 1
                if counter > 1000:
                    new_slug = page.public_id or f"page-{page.id}"
                    break
            
            if dry_run:
                self.stdout.write(
                    f'Would update: {page.name} '
                    f'(ID: {page.id}, Type: {page.page_type}) -> {new_slug}'
                )
            else:
                old_slug = page.slug or '(empty)'
                page.slug = new_slug
                page.save(update_fields=['slug'])
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated: {page.name} '
                        f'({old_slug} -> {new_slug})'
                    )
                )
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN: Would update {updated_count} pages'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nCompleted: Updated {updated_count} pages, '
                    f'skipped {skipped_count} pages'
                )
            )



