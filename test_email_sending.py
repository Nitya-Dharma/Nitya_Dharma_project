"""
Test email sending to verify SMTP is working
"""
import os
import logging
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')

# Configure logging to see all messages
logging.basicConfig(
    level=logging.WARNING,  # Show WARNING and above
    format='%(levelname)s - %(name)s - %(message)s'
)

import django
django.setup()

from django.core.mail import send_mail
from django.conf import settings
from accounts.models import User, EmailVerificationToken
from accounts.email_verification import create_email_verification

print("=" * 60)
print("EMAIL SENDING TEST")
print("=" * 60)
print()

# Test 1: Check configuration
print("1. Email Configuration:")
print(f"   EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"   EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"   EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"   EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"   EMAIL_HOST_USER: {'SET' if settings.EMAIL_HOST_USER else 'NOT SET'}")
print(f"   EMAIL_HOST_PASSWORD: {'SET' if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
print(f"   DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
print()

# Test 2: Direct send_mail test
print("2. Testing direct send_mail()...")
test_email = input("Enter your email address to test: ").strip()
if not test_email:
    print("No email provided. Skipping direct test.")
else:
    try:
        send_mail(
            subject='Test Email - Nitya Dharma',
            message='This is a test email. If you receive this, SMTP is working!',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        print(f"   ✓ Email sent to {test_email}")
        print("   Check your inbox (and spam folder)")
    except Exception as e:
        print(f"   ✗ Failed to send email: {e}")
        import traceback
        traceback.print_exc()
print()

# Test 3: Check recent registrations
print("3. Checking recent Pandit registrations...")
recent_users = User.objects.filter(role='pandit').order_by('-date_joined')[:5]
print(f"   Found {recent_users.count()} recent Pandit users:")
for user in recent_users:
    print(f"   - {user.email} (created: {user.date_joined})")
    tokens = EmailVerificationToken.objects.filter(user=user, is_used=False).order_by('-created_at')
    print(f"     Active tokens: {tokens.count()}")
    if tokens.exists():
        latest = tokens.first()
        print(f"     Latest token created: {latest.created_at}")
        print(f"     Token expires: {latest.expires_at}")
print()

# Test 4: Test create_email_verification for existing user
if recent_users.exists():
    test_user = recent_users.first()
    print(f"4. Testing create_email_verification() for {test_user.email}...")
    try:
        from django.db import transaction
        with transaction.atomic():
            token = create_email_verification(test_user)
            print(f"   ✓ Token created: {token.token[:20]}...")
            print(f"   ✓ Transaction committed - email should be sent")
            print("   Check Django server terminal for [EMAIL DEBUG] logs")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("4. No Pandit users found. Skipping verification test.")
print()

print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print()
print("Next steps:")
print("1. If direct send_mail() worked, check your inbox")
print("2. If it didn't work, check SMTP credentials in .env")
print("3. Check Django server terminal for [EMAIL DEBUG] logs during registration")
print("4. Check spam folder in your email")












