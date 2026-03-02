"""
Quick script to resend verification email for a Pandit user.

Usage:
    python resend_verification_quick.py <email>
    
Example:
    python resend_verification_quick.py kabdeshriya2005@gmail.com
"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
import django
django.setup()

from accounts.models import User
from accounts.services import (
    resend_verification_email,
    VerificationAlreadyCompleted,
    CooldownNotElapsed
)

if len(sys.argv) < 2:
    print("Usage: python resend_verification_quick.py <email>")
    print("Example: python resend_verification_quick.py kabdeshriya2005@gmail.com")
    sys.exit(1)

email = sys.argv[1]

print("=" * 60)
print("RESEND VERIFICATION EMAIL")
print("=" * 60)
print()

try:
    # Find user
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        print(f"[ERROR] User with email '{email}' does not exist.")
        sys.exit(1)

    # Check role
    if user.role != 'pandit':
        print(f"[ERROR] User '{email}' is not a Pandit.")
        print("Email verification resend is only available for Pandit accounts.")
        sys.exit(1)

    # Check verification status
    print(f"User: {user.email}")
    print(f"Role: {user.role}")
    print(f"Email Verified: {user.email_verified}")
    print(f"Email Verified At: {user.email_verified_at}")
    print()

    # Resend verification
    try:
        token = resend_verification_email(user)
        print("=" * 60)
        print("[SUCCESS] Verification email resent successfully!")
        print("=" * 60)
        print(f"Email sent to: {user.email}")
        print(f"Token ID: {token.public_id}")
        print(f"Token expires at: {token.expires_at}")
        print()
        print("Please check inbox and spam folder for the verification email.")
        print("=" * 60)
    except VerificationAlreadyCompleted:
        print("=" * 60)
        print("[INFO] User is already verified.")
        print("=" * 60)
        print(f"User '{email}' has already verified their email.")
        print("No action needed.")
        print("=" * 60)
    except CooldownNotElapsed as e:
        print("=" * 60)
        print("[WARNING] Cooldown period not elapsed")
        print("=" * 60)
        print(str(e))
        print("=" * 60)
    except Exception as e:
        print("=" * 60)
        print("[ERROR] Failed to resend verification email")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)

except Exception as e:
    print("=" * 60)
    print("[ERROR] Unexpected error")
    print("=" * 60)
    print(f"Error: {str(e)}")
    print("=" * 60)
    import traceback
    traceback.print_exc()
    sys.exit(1)












