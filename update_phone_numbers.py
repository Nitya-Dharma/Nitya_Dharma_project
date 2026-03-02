"""
Script to update existing users with phone numbers.

This script adds phone numbers to all existing users (pandits and regular users)
if they don't already have them.

Run this script:
    python update_phone_numbers.py
"""

import os
import django

# Setup Django - must be done before any imports
# Use same settings module as populate_dummy_data.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
django.setup()

# Import models after Django setup
from accounts.models import User


def update_phone_numbers():
    """Update all users with phone numbers if missing"""
    print("\n[PHONE] Updating Phone Numbers for All Users...")
    
    # Phone numbers for existing users
    phone_mapping = {
        # Super Admin
        'admin@nityadharma.com': {
            'phone': '+919999999999',
            'whatsapp': '+919999999999'
        },
        # Admin Pandit
        'adminpandit@nityadharma.com': {
            'phone': '+919888888888',
            'whatsapp': '+919888888888'
        },
        # Pandits
        'pandit1@nityadharma.com': {
            'phone': '+919876543210',
            'whatsapp': '+919876543210'
        },
        'pandit2@nityadharma.com': {
            'phone': '+919876543211',
            'whatsapp': '+919876543211'
        },
        'pandit3@nityadharma.com': {
            'phone': '+919876543212',
            'whatsapp': '+919876543212'
        },
        'pandit4@nityadharma.com': {
            'phone': '+919876543213',
            'whatsapp': '+919876543213'
        },
        # Regular Users
        'user1@nityadharma.com': {
            'phone': '+919777777777',
            'whatsapp': '+919777777777'
        },
        'user2@nityadharma.com': {
            'phone': '+919666666666',
            'whatsapp': '+919666666666'
        },
        'user3@nityadharma.com': {
            'phone': '+919555555555',
            'whatsapp': '+919555555555'
        },
    }
    
    updated_count = 0
    skipped_count = 0
    
    # Update users with known emails
    for email, numbers in phone_mapping.items():
        try:
            user = User.objects.get(email=email)
            updated = False
            
            if not user.phone_number:
                user.phone_number = numbers['phone']
                updated = True
            
            if not user.whatsapp_number:
                user.whatsapp_number = numbers['whatsapp']
                updated = True
            
            if updated:
                user.save()
                print(f"  [OK] Updated {user.get_full_name()} ({email}): {numbers['phone']}")
                updated_count += 1
            else:
                print(f"  [INFO] {user.get_full_name()} ({email}) already has phone numbers")
                skipped_count += 1
        except User.DoesNotExist:
            print(f"  [WARN] User not found: {email}")
    
    # Update all other pandits with random phone numbers
    all_pandits = User.objects.filter(role='pandit')
    base_number = 919876543220
    
    for i, pandit in enumerate(all_pandits):
        if pandit.email not in phone_mapping:
            if not pandit.phone_number:
                phone = f"+91{base_number + i}"
                pandit.phone_number = phone
                pandit.whatsapp_number = phone
                pandit.save()
                print(f"  [OK] Updated Pandit {pandit.get_full_name()} ({pandit.email}): {phone}")
                updated_count += 1
    
    print(f"\n[SUCCESS] Phone Number Update Complete!")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count}")
    
    # Display summary
    pandits_with_phone = User.objects.filter(role='pandit', phone_number__isnull=False).count()
    total_pandits = User.objects.filter(role='pandit').count()
    print(f"\n[STATS] Pandits with phone numbers: {pandits_with_phone}/{total_pandits}")


if __name__ == '__main__':
    update_phone_numbers()

