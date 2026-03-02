"""
Management command to load authoritative pooja master data.

This command loads the FINAL, AUTHORITATIVE list of poojas.
Only Super Admin can run this command.

Categories:
- A. Daily & Common Household Poojas
- B. House, Property & Vehicle Poojas
- C. Important Life Samskaras
- D. Festival & Temple Poojas
- E. Homams / Fire Rituals
- F. Yagnas
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from masterdata.models import Pooja


class Command(BaseCommand):
    help = 'Load authoritative pooja master data (Super Admin only)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating poojas',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing poojas (by default, skips existing)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        # Authoritative pooja list (FINAL)
        AUTHORITATIVE_POOJAS = [
            # A. Daily & Common Household Poojas
            ('Ganapati Puja', 'daily_household'),
            ('Navagraha Puja', 'daily_household'),
            ('Satyanarayana Vratam', 'daily_household'),
            ('Lakshmi Puja', 'daily_household'),
            ('Durga Puja', 'daily_household'),
            ('Hanuman Puja', 'daily_household'),
            ('Rudrabhishekam', 'daily_household'),
            
            # B. House, Property & Vehicle Poojas
            ('Bhoomi Puja', 'house_property_vehicle'),
            ('Gruha Pravesam', 'house_property_vehicle'),
            ('Vastu Shanti Puja', 'house_property_vehicle'),
            ('Vehicle Puja', 'house_property_vehicle'),
            
            # C. Important Life Samskaras
            ('Namakarana', 'life_samskaras'),
            ('Annaprashanam', 'life_samskaras'),
            ('Upanayanam', 'life_samskaras'),
            ('Vivaha Puja', 'life_samskaras'),
            ('Saptapadi', 'life_samskaras'),
            
            # D. Festival & Temple Poojas
            ('Vinayaka Chaturthi', 'festival_temple'),
            ('Navaratri Puja', 'festival_temple'),
            ('Diwali Puja', 'festival_temple'),
            
            # E. Homams / Fire Rituals
            ('Ganapathi Homam', 'homams'),
            ('Navagraha Homam', 'homams'),
            ('Mrityunjaya Homam', 'homams'),
            ('Durga Homam', 'homams'),
            
            # F. Yagnas
            ('Satyanarayana Yagna', 'yagnas'),
            ('Putrakameshti Yagna', 'yagnas'),
            ('Ashvamedha Yagna', 'yagnas'),
        ]
        
        self.stdout.write('=' * 80)
        self.stdout.write('LOADING AUTHORITATIVE POOJA MASTER DATA')
        self.stdout.write('=' * 80)
        self.stdout.write('')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No poojas will be created'))
            self.stdout.write('')
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        with transaction.atomic():
            for pooja_name, category in AUTHORITATIVE_POOJAS:
                try:
                    pooja, created = Pooja.objects.get_or_create(
                        name=pooja_name,
                        defaults={
                            'category': category,
                            'is_active': True,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  [CREATED] {pooja_name} ({category})')
                        )
                    else:
                        # Pooja already exists
                        if force:
                            # Update category if forced
                            if pooja.category != category:
                                pooja.category = category
                                pooja.is_active = True
                                pooja.save()
                                updated_count += 1
                                self.stdout.write(
                                    self.style.WARNING(f'  [UPDATED] {pooja_name} ({category})')
                                )
                            else:
                                skipped_count += 1
                                self.stdout.write(
                                    self.style.NOTICE(f'  [SKIPPED] {pooja_name} (already exists)')
                                )
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.NOTICE(f'  [SKIPPED] {pooja_name} (already exists)')
                            )
                            
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  [ERROR] Failed to create {pooja_name}: {str(e)}')
                    )
            
            if dry_run:
                # Rollback transaction in dry-run mode
                transaction.set_rollback(True)
        
        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write('SUMMARY')
        self.stdout.write('=' * 80)
        self.stdout.write(f'Total poojas in authoritative list: {len(AUTHORITATIVE_POOJAS)}')
        self.stdout.write(f'Created: {created_count}')
        if force:
            self.stdout.write(f'Updated: {updated_count}')
        self.stdout.write(f'Skipped: {skipped_count}')
        self.stdout.write('')
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('Authoritative pooja master data loaded successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes made. Run without --dry-run to create poojas.')
            )
        
        self.stdout.write('=' * 80)












