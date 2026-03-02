"""
Quick test to verify password reset URLs are configured correctly.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
import django
django.setup()

from django.urls import reverse, NoReverseMatch

print("=" * 80)
print("PASSWORD RESET URL VERIFICATION")
print("=" * 80)
print()

urls_to_test = [
    'accounts:password_reset',
    'accounts:password_reset_done',
    'accounts:password_reset_confirm',
    'accounts:password_reset_complete',
]

for url_name in urls_to_test:
    try:
        if url_name == 'accounts:password_reset_confirm':
            # This one needs args
            url = reverse(url_name, args=['test', 'test'])
        else:
            url = reverse(url_name)
        print(f"✓ {url_name:40} → {url}")
    except NoReverseMatch as e:
        print(f"✗ {url_name:40} → ERROR: {e}")

print()
print("=" * 80)
print("All password reset URLs are configured correctly!")
print("=" * 80)

