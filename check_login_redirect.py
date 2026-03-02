"""Check login redirect for a specific user"""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
import django
django.setup()

from accounts.models import User

if len(sys.argv) < 2:
    print("Usage: python check_login_redirect.py <email>")
    print("Example: python check_login_redirect.py shruthi130503@gmail.com")
    sys.exit(1)

email = sys.argv[1]

print("=" * 80)
print("LOGIN REDIRECT CHECK")
print("=" * 80)
print()

try:
    user = User.objects.get(email=email)
    
    print(f"User Email: {user.email}")
    print(f"Role: {user.role}")
    print(f"is_superuser: {user.is_superuser}")
    print(f"is_staff: {user.is_staff}")
    print(f"is_active: {user.is_active}")
    print()
    
    print("REDIRECT LOGIC:")
    print("-" * 80)
    
    # Simulate login redirect logic
    if user.is_superuser:
        redirect_to = "dashboard_super_admin"
        reason = "is_superuser = True"
    elif user.role == 'admin':
        redirect_to = "dashboard_admin_pandit"
        reason = "role = 'admin' (Admin Pandit)"
    elif user.role == 'pandit':
        redirect_to = "dashboard_pandit"
        reason = "role = 'pandit' (Regular Pandit)"
    else:
        redirect_to = "core:home"
        reason = f"role = '{user.role}' (End User)"
    
    print(f"Will redirect to: {redirect_to}")
    print(f"Reason: {reason}")
    print()
    
    print("=" * 80)
    print("DIAGNOSIS:")
    print("=" * 80)
    
    if user.role == 'pandit' and redirect_to == "dashboard_pandit":
        print("[OK] User will correctly redirect to Pandit Dashboard")
    elif user.role == 'pandit' and redirect_to != "dashboard_pandit":
        print("[ERROR] User has role='pandit' but will redirect to wrong dashboard!")
        print(f"        Expected: dashboard_pandit")
        print(f"        Actual: {redirect_to}")
        print()
        print("SOLUTION: This should not happen. Check login view code.")
    elif user.role == 'admin' and not user.is_superuser:
        print("[INFO] User is an Admin Pandit (role='admin')")
        print("       They will correctly redirect to Admin Pandit Dashboard")
        print()
        print("NOTE: If you want this user to go to Pandit Dashboard instead:")
        print("      Change their role to 'pandit' in database")
        print("      But this will remove their admin privileges")
    else:
        print(f"[INFO] User will redirect to {redirect_to}")
        
except User.DoesNotExist:
    print(f"[ERROR] User with email '{email}' does not exist")
    print()
    print("Available users:")
    for u in User.objects.all()[:10]:
        print(f"  - {u.email} (role={u.role})")
    sys.exit(1)

print()
print("=" * 80)












