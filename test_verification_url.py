"""Test verification URL building"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
import django
django.setup()

from django.conf import settings
from django.urls import reverse

print("=" * 60)
print("VERIFICATION URL BUILDING TEST")
print("=" * 60)
print()

# Check SITE_URL
site_url = getattr(settings, 'SITE_URL', None)
print(f"1. SITE_URL Setting:")
print(f"   {site_url if site_url else 'NOT SET (will use default)'}")
print()

# Test URL pattern
print("2. URL Pattern Test:")
try:
    url = reverse('accounts:verify_email', args=['test-token-123'])
    print(f"   Relative path: {url}")
    
    # Build full URL
    if not site_url:
        site_url = 'http://127.0.0.1:8000'
    
    site_url = site_url.rstrip('/')
    if not url.startswith('/'):
        url = '/' + url
    
    full_url = f"{site_url}{url}"
    print(f"   Full URL: {full_url}")
    print()
    
    # Check for malformed URL
    if '://' in url or ':http' in full_url:
        print("   [ERROR] URL is malformed!")
    else:
        print("   [OK] URL is correctly formatted")
    
except Exception as e:
    print(f"   [ERROR] {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)












