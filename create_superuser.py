"""
Script to create a Django superuser non-interactively.

Run this script to create a superuser account for Django admin access.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
django.setup()

from accounts.models import User

def create_superuser():
    """admin@nityadharma.com
    Create a superuser account.
    
    Modify the email and password below before running.
    """
    email = 'admin@nityadharma.com'  # Change this to your desired email
    password = 'admin123'  # Change this to a secure password
    
    # Check if superuser already exists
    if User.objects.filter(email=email, is_superuser=True).exists():
        user = User.objects.get(email=email)
        print(f"[INFO] Superuser with email '{email}' already exists!")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   Status: {user.status}")
        print(f"   Is Active: {user.is_active}")
        print(f"   Is Staff: {user.is_staff}")
        print(f"   Is Superuser: {user.is_superuser}")
        print()
        print("To reset password, use:")
        print(f"   python manage.py changepassword {email}")
        return
    
    # Create superuser
    try:
        user = User.objects.create_superuser(
            email=email,
            password=password,
            role='admin',  # Set role to admin
            status='active',  # Set status to active
            email_verified=True,  # Skip email verification for superuser
        )
        print(f"[OK] Superuser created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: {user.role}")
        print(f"   Status: {user.status}")
        print(f"   Is Active: {user.is_active}")
        print(f"   Is Staff: {user.is_staff}")
        print(f"   Is Superuser: {user.is_superuser}")
        print()
        print("[WARNING] Change the password after first login!")
    except Exception as e:
        print(f"[ERROR] Error creating superuser: {e}")

if __name__ == '__main__':
    create_superuser()

