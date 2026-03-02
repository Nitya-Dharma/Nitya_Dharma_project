"""
Script to create 2 sample temple pages for testing.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings')
django.setup()

from accounts.models import User
from pages.services import create_page
from pages.constants import PAGE_TYPE_TEMPLE

def create_sample_pages():
    """Create 2 sample temple pages."""
    # Get admin user
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.filter(role='admin').first()
    
    if not admin:
        print("ERROR: No admin user found. Please create an admin user first.")
        return
    
    print(f"Using user: {admin.email}")
    print("=" * 60)
    
    # Page 1
    print("\nCreating Sample Temple Page 1...")
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
        print(f"✓ Page 1 created successfully!")
        print(f"  Title: {page1.title}")
        print(f"  Public ID: {page1.public_id}")
        print(f"  Slug: {page1.slug}")
        print(f"  Status: {page1.status}")
    except Exception as e:
        print(f"✗ Failed to create Page 1: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # Page 2
    print("\nCreating Sample Temple Page 2...")
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
        print(f"✓ Page 2 created successfully!")
        print(f"  Title: {page2.title}")
        print(f"  Public ID: {page2.public_id}")
        print(f"  Slug: {page2.slug}")
        print(f"  Status: {page2.status}")
    except Exception as e:
        print(f"✗ Failed to create Page 2: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("SUCCESS: Both sample temple pages created successfully!")
    print("=" * 60)

if __name__ == '__main__':
    create_sample_pages()



















