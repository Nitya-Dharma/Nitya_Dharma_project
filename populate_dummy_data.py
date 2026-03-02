"""
Script to populate the database with dummy data for testing and demonstration.

This script creates:
- Master data (Cities, Areas, Poojas)
- Users (Super Admin, Admin Pandit, Regular Pandits, Regular Users)
- Referral Links
- Pandit Profiles
- Availability entries
- Booking Intents
- Reviews

Run this script after migrations:
    python populate_dummy_data.py
"""

import os
import django
from datetime import date, time, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
django.setup()

from accounts.models import User
from masterdata.models import City, LocalArea, Pooja
from referrals.models import ReferralLink
from profiles.models import PanditProfile
from availability.models import Availability
from booking_intent.models import BookingIntent
from reviews.models import Review


def create_master_data():
    """Create master data: Cities, Areas, Poojas"""
    print("\n[MASTER DATA] Creating Master Data...")
    
    # Cities
    cities_data = [
        {'name': 'Mumbai', 'state': 'Maharashtra'},
        {'name': 'Delhi', 'state': 'Delhi'},
        {'name': 'Bangalore', 'state': 'Karnataka'},
        {'name': 'Pune', 'state': 'Maharashtra'},
        {'name': 'Hyderabad', 'state': 'Telangana'},
    ]
    
    cities = {}
    for city_data in cities_data:
        city, created = City.objects.get_or_create(
            name=city_data['name'],
            defaults={'state': city_data['state']}
        )
        cities[city_data['name']] = city
        if created:
            print(f"  [OK] Created city: {city.name}")
    
    # Areas
    areas_data = [
        {'name': 'Andheri', 'city': 'Mumbai'},
        {'name': 'Bandra', 'city': 'Mumbai'},
        {'name': 'Connaught Place', 'city': 'Delhi'},
        {'name': 'Koramangala', 'city': 'Bangalore'},
        {'name': 'Hinjewadi', 'city': 'Pune'},
        {'name': 'Hitech City', 'city': 'Hyderabad'},
    ]
    
    areas = {}
    for area_data in areas_data:
        area, created = LocalArea.objects.get_or_create(
            name=area_data['name'],
            city=cities[area_data['city']],
            defaults={}
        )
        areas[area_data['name']] = area
        if created:
            print(f"  [OK] Created area: {area.name}, {area.city.name}")
    
    # Poojas - All categories with complete list
    poojas_data = [
        # Daily & Common Household Poojas
        {'name': 'Ganapati Puja', 'description': 'Worship of Lord Ganesha, remover of obstacles'},
        {'name': 'Ganesh Puja', 'description': 'Worship of Lord Ganesha'},
        {'name': 'Ganapathi Puja', 'description': 'Worship of Lord Ganesha'},
        {'name': 'Navagraha Puja', 'description': 'Worship of nine planets for astrological peace'},
        {'name': 'Satyanarayana Vratam', 'description': 'Ritual to please Lord Vishnu for blessings'},
        {'name': 'Satyanarayan Vratam', 'description': 'Ritual to please Lord Vishnu for blessings'},
        {'name': 'Satyanarayana Puja', 'description': 'Worship of Lord Satyanarayana'},
        {'name': 'Lakshmi Puja', 'description': 'Worship of Goddess Lakshmi for wealth'},
        {'name': 'Laxmi Puja', 'description': 'Worship of Goddess Lakshmi for wealth'},
        {'name': 'Durga Puja', 'description': 'Worship of Goddess Durga for protection'},
        {'name': 'Hanuman Puja', 'description': 'Worship of Lord Hanuman for strength'},
        {'name': 'Rudrabhishekam', 'description': 'Special worship of Lord Shiva'},
        {'name': 'Rudra Abhishekam', 'description': 'Special worship of Lord Shiva'},
        {'name': 'Rudra Puja', 'description': 'Worship of Lord Shiva'},
        
        # House, Property & Vehicle Poojas
        {'name': 'Bhoomi Puja', 'description': 'Worship and respect for the land'},
        {'name': 'Gruha Pravesam', 'description': 'Housewarming ceremony before moving in'},
        {'name': 'Gruha Pravesh', 'description': 'Housewarming ceremony before moving in'},
        {'name': 'Vastu Shanti Puja', 'description': 'Correcting vastu doshas for harmony'},
        {'name': 'Vehicle Puja', 'description': 'Worship of vehicles for safety'},
        
        # Important Life Samskaras (Ceremonies)
        {'name': 'Namakarana', 'description': 'Baby naming ceremony'},
        {'name': 'Namkaran', 'description': 'Baby naming ceremony'},
        {'name': 'Annaprashanam', 'description': 'First feeding ceremony for baby'},
        {'name': 'Upanayanam', 'description': 'Sacred thread ceremony for boys'},
        {'name': 'Vivaha Puja', 'description': 'Wedding rituals'},
        {'name': 'Vivah Puja', 'description': 'Wedding rituals'},
        {'name': 'Saptapadi', 'description': 'Seven steps ceremony during weddings'},
        
        # Festival & Temple Poojas
        {'name': 'Vinayaka Chaturthi', 'description': 'Festival worship of Lord Ganesha'},
        {'name': 'Navaratri Puja', 'description': 'Nine nights festival in honor of Goddess Durga'},
        {'name': 'Navratri Puja', 'description': 'Nine nights festival in honor of Goddess Durga'},
        {'name': 'Diwali Puja', 'description': 'Festival of lights, worship of Lakshmi & Ganesha'},
        {'name': 'Deepavali Puja', 'description': 'Festival of lights, worship of Lakshmi & Ganesha'},
        
        # Homams / Fire Rituals
        {'name': 'Ganapathi Homam', 'description': 'Fire ritual to invoke Lord Ganesha'},
        {'name': 'Ganapati Homam', 'description': 'Fire ritual to invoke Lord Ganesha'},
        {'name': 'Navagraha Homam', 'description': 'Homa for nine planets'},
        {'name': 'Mrityunjaya Homam', 'description': 'Powerful fire ritual for health and longevity'},
        {'name': 'Durga Homam', 'description': 'Fire ritual inviting Goddess Durga'},
        
        # Yagnas (Vedic Offerings)
        {'name': 'Satyanarayana Yagna', 'description': 'Special yajna for prosperity and blessings'},
        {'name': 'Satyanarayana Yajna', 'description': 'Special yajna for prosperity and blessings'},
        {'name': 'Putrakameshti Yagna', 'description': 'Yagna to pray for a male child'},
        {'name': 'Putrakameshti Yajna', 'description': 'Yagna to pray for a male child'},
        {'name': 'Ashvamedha Yagna', 'description': 'Ancient royal horse sacrifice yajna'},
        {'name': 'Ashvamedha Yajna', 'description': 'Ancient royal horse sacrifice yajna'},
    ]
    
    poojas = {}
    for pooja_data in poojas_data:
        pooja, created = Pooja.objects.get_or_create(
            name=pooja_data['name'],
            defaults={'description': pooja_data['description']}
        )
        poojas[pooja_data['name']] = pooja
        if created:
            print(f"  [OK] Created pooja: {pooja.name}")
    
    return cities, areas, poojas


def create_users():
    """Create users: Super Admin, Admin Pandit, Pandits, Regular Users"""
    print("\n[USERS] Creating Users...")
    
    users = {}
    
    # Super Admin
    super_admin, created = User.objects.get_or_create(
        email='admin@nityadharma.com',
        defaults={
            'username': 'superadmin',
            'first_name': 'Super',
            'last_name': 'Admin',
            'role': 'admin',
            'status': 'active',
            'is_superuser': True,
            'is_staff': True,
            'is_active': True,
            'phone_number': '+919999999999',
            'whatsapp_number': '+919999999999',
        }
    )
    if created:
        super_admin.set_password('admin123')
        super_admin.save()
        print(f"  [OK] Created Super Admin: {super_admin.email}")
    else:
        print(f"  [INFO] Super Admin already exists: {super_admin.email}")
    users['super_admin'] = super_admin
    
    # Admin Pandit
    admin_pandit, created = User.objects.get_or_create(
        email='adminpandit@nityadharma.com',
        defaults={
            'username': 'adminpandit',
            'first_name': 'Admin',
            'last_name': 'Pandit',
            'role': 'admin',
            'status': 'active',
            'is_active': True,
            'phone_number': '+919888888888',
            'whatsapp_number': '+919888888888',
        }
    )
    if created:
        admin_pandit.set_password('admin123')
        admin_pandit.save()
        print(f"  [OK] Created Admin Pandit: {admin_pandit.email}")
    users['admin_pandit'] = admin_pandit
    
    # Regular Pandits
    pandits_data = [
               {
                   'email': 'pandit1@nityadharma.com',
                   'username': 'pandit1',
                   'first_name': 'Ramesh',
                   'last_name': 'Sharma',
                   'role': 'pandit',
                   'status': 'active',
                   'phone_number': '+919876543210',
                   'whatsapp_number': '+919876543210',
               },
               {
                   'email': 'pandit2@nityadharma.com',
                   'username': 'pandit2',
                   'first_name': 'Suresh',
                   'last_name': 'Kumar',
                   'role': 'pandit',
                   'status': 'active',
                   'phone_number': '+919876543211',
                   'whatsapp_number': '+919876543211',
               },
               {
                   'email': 'pandit3@nityadharma.com',
                   'username': 'pandit3',
                   'first_name': 'Mahesh',
                   'last_name': 'Patel',
                   'role': 'pandit',
                   'status': 'active',
                   'phone_number': '+919876543212',
                   'whatsapp_number': '+919876543212',
               },
               {
                   'email': 'pandit4@nityadharma.com',
                   'username': 'pandit4',
                   'first_name': 'Krishna',
                   'last_name': 'Iyer',
                   'role': 'pandit',
                   'status': 'active',
                   'phone_number': '+919876543213',
                   'whatsapp_number': '+919876543213',
               },
           ]
    
    for i, pandit_data in enumerate(pandits_data, 1):
        pandit, created = User.objects.get_or_create(
            email=pandit_data['email'],
            defaults=pandit_data
        )
        if created:
            pandit.set_password('pandit123')
            pandit.is_active = (pandit_data['status'] == 'active')
            pandit.save()
            print(f"  [OK] Created Pandit {i}: {pandit.email} (Status: {pandit.status})")
        else:
            # Update existing pandit with phone numbers if missing
            updated = False
            if not pandit.phone_number and 'phone_number' in pandit_data:
                pandit.phone_number = pandit_data['phone_number']
                updated = True
            if not pandit.whatsapp_number and 'whatsapp_number' in pandit_data:
                pandit.whatsapp_number = pandit_data['whatsapp_number']
                updated = True
            if updated:
                pandit.save()
                print(f"  🔄 Updated Pandit {i} phone numbers: {pandit.email}")
        users[f'pandit{i}'] = pandit
    
    # Regular Users
    users_data = [
        {
            'email': 'user1@nityadharma.com',
            'username': 'user1',
            'first_name': 'Raj',
            'last_name': 'Singh',
            'role': 'user',
            'status': 'active',
            'phone_number': '+919777777777',
            'whatsapp_number': '+919777777777',
        },
        {
            'email': 'user2@nityadharma.com',
            'username': 'user2',
            'first_name': 'Priya',
            'last_name': 'Patel',
            'role': 'user',
            'status': 'active',
            'phone_number': '+919666666666',
            'whatsapp_number': '+919666666666',
        },
        {
            'email': 'user3@nityadharma.com',
            'username': 'user3',
            'first_name': 'Amit',
            'last_name': 'Kumar',
            'role': 'user',
            'status': 'active',
            'phone_number': '+919555555555',
            'whatsapp_number': '+919555555555',
        },
    ]
    
    for i, user_data in enumerate(users_data, 1):
        user, created = User.objects.get_or_create(
            email=user_data['email'],
            defaults=user_data
        )
        if created:
            user.set_password('user123')
            user.is_active = True
            user.save()
            print(f"  [OK] Created User {i}: {user.email}")
        else:
            # Update existing user with phone numbers if missing
            updated = False
            if not user.phone_number and 'phone_number' in user_data:
                user.phone_number = user_data['phone_number']
                updated = True
            if not user.whatsapp_number and 'whatsapp_number' in user_data:
                user.whatsapp_number = user_data['whatsapp_number']
                updated = True
            if updated:
                user.save()
                print(f"  🔄 Updated User {i} phone numbers: {user.email}")
        users[f'user{i}'] = user
    
    return users


def create_referral_links(users):
    """Create referral links"""
    print("\n[REFERRALS] Creating Referral Links...")
    
    # Create referral link by Super Admin
    import secrets
    token1 = secrets.token_hex(16)
    referral_link1, created = ReferralLink.objects.get_or_create(
        token=token1,
        defaults={
            'created_by': users['super_admin'],
            'referral_code': token1,
            'max_uses': 5,
            'used_count': 2,  # Already used 2 times
            'is_active': True,
        }
    )
    if created:
        print(f"  [OK] Created Referral Link 1: {token1[:16]}... (Used: 2/5)")
    
    # Create another referral link by Admin Pandit
    token2 = secrets.token_hex(16)
    referral_link2, created = ReferralLink.objects.get_or_create(
        token=token2,
        defaults={
            'created_by': users['admin_pandit'],
            'referral_code': token2,
            'max_uses': 5,
            'used_count': 0,
            'is_active': True,
        }
    )
    if created:
        print(f"  [OK] Created Referral Link 2: {token2[:16]}... (Used: 0/5)")
    
    return {'link1': referral_link1, 'link2': referral_link2}


def create_pandit_profiles(users, cities, areas, poojas):
    """Create Pandit profiles"""
    print("\n[PROFILES] Creating Pandit Profiles...")
    
    profiles = {}
    
    # Pandit 1 Profile
    pandit1 = users['pandit1']
    profile1, created = PanditProfile.objects.get_or_create(
        user=pandit1,
        defaults={
            'display_name': 'Pandit Ramesh Sharma',
            'about_description': 'Experienced Pandit with 15 years of practice. Specialized in Ganesh Pooja and Satyanarayan Pooja. Fluent in Hindi, English, and Marathi.',
            'experience_years': 15,
            'languages_spoken': 'Hindi, English, Marathi',
            # Note: city and area are ManyToMany fields (cities_served, areas_served), not ForeignKey
            # They must be added after creation using .add()
        }
    )
    if created:
        profile1.poojas_performed.add(poojas['Ganesh Pooja'], poojas['Satyanarayan Pooja'])
        profile1.cities_served.add(cities['Mumbai'], cities['Pune'])
        profile1.areas_served.add(areas['Andheri'], areas['Bandra'])
        print(f"  [OK] Created profile for {pandit1.email}")
    profiles['pandit1'] = profile1
    
    # Pandit 2 Profile
    pandit2 = users['pandit2']
    profile2, created = PanditProfile.objects.get_or_create(
        user=pandit2,
        defaults={
            'display_name': 'Pandit Suresh Kumar',
            'about_description': 'Renowned Pandit specializing in marriage ceremonies and house warming poojas. 20 years of experience.',
            'experience_years': 20,
            'languages_spoken': 'Hindi, English',
            # Note: city and area are ManyToMany fields (cities_served, areas_served), not ForeignKey
            # They must be added after creation using .add()
        }
    )
    if created:
        profile2.poojas_performed.add(poojas['Vivah Sanskar'], poojas['Griha Pravesh'], poojas['Lakshmi Pooja'])
        profile2.cities_served.add(cities['Delhi'])
        profile2.areas_served.add(areas['Connaught Place'])
        print(f"  [OK] Created profile for {pandit2.email}")
    profiles['pandit2'] = profile2
    
    # Pandit 3 Profile (Pending - no profile yet)
    print(f"  [INFO] Pandit 3 ({users['pandit3'].email}) is pending approval - no profile created")
    
    return profiles


def create_availability(users, profiles, cities, areas):
    """Create availability entries for Pandits"""
    print("\n[AVAILABILITY] Creating Availability...")
    
    # Pandit 1 Availability (Mumbai, Andheri)
    pandit1 = users['pandit1']
    avail1, created = Availability.objects.get_or_create(
        pandit=pandit1,
        day_of_week=Availability.MONDAY,
        city=cities['Mumbai'],
        defaults={
            'start_time': time(9, 0),
            'end_time': time(18, 0),
            'is_recurring': True,
            'area': areas['Andheri'],
        }
    )
    if created:
        print(f"  [OK] Created availability for {pandit1.email}: Monday 9 AM - 6 PM (Mumbai, Andheri)")
    
    avail2, created = Availability.objects.get_or_create(
        pandit=pandit1,
        day_of_week=Availability.TUESDAY,
        city=cities['Mumbai'],
        defaults={
            'start_time': time(9, 0),
            'end_time': time(18, 0),
            'is_recurring': True,
            'area': areas['Andheri'],
        }
    )
    if created:
        print(f"  [OK] Created availability for {pandit1.email}: Tuesday 9 AM - 6 PM (Mumbai, Andheri)")
    
    # Pandit 2 Availability (Delhi, Connaught Place)
    pandit2 = users['pandit2']
    avail3, created = Availability.objects.get_or_create(
        pandit=pandit2,
        day_of_week=Availability.SATURDAY,
        city=cities['Delhi'],
        defaults={
            'start_time': time(10, 0),
            'end_time': time(20, 0),
            'is_recurring': True,
            'area': areas['Connaught Place'],
        }
    )
    if created:
        print(f"  [OK] Created availability for {pandit2.email}: Saturday 10 AM - 8 PM (Delhi, Connaught Place)")
    
    avail4, created = Availability.objects.get_or_create(
        pandit=pandit2,
        day_of_week=Availability.SUNDAY,
        city=cities['Delhi'],
        defaults={
            'start_time': time(10, 0),
            'end_time': time(20, 0),
            'is_recurring': True,
            'area': areas['Connaught Place'],
        }
    )
    if created:
        print(f"  [OK] Created availability for {pandit2.email}: Sunday 10 AM - 8 PM (Delhi, Connaught Place)")


def create_booking_intents(users):
    """Create booking intents with various statuses for testing"""
    print("\n[BOOKING INTENTS] Creating Booking Intents...")
    
    # Get all active pandits
    active_pandits = [users.get('pandit1'), users.get('pandit2')]
    active_pandits = [p for p in active_pandits if p]
    
    if not active_pandits:
        print("  ⚠️  No active pandits found, skipping booking intents")
        return
    
    # User 1 → Pandit 1 (Submitted)
    intent1, created = BookingIntent.objects.get_or_create(
        requester=users['user1'],
        pandit=users['pandit1'],
        defaults={
            'optional_requested_date': date.today() + timedelta(days=7),
            'optional_requested_time': time(10, 0),
            'message': 'Need Ganesh Pooja for house warming ceremony',
            'status': BookingIntent.STATUS_SUBMITTED,
            'requester_status_at_creation': users['user1'].status,
            'pandit_status_at_creation': users['pandit1'].status,
        }
    )
    if created:
        print(f"  [OK] Created booking intent: {users['user1'].email} -> {users['pandit1'].email} (Submitted)")
    
    # User 2 → Pandit 2 (Viewed)
    intent2, created = BookingIntent.objects.get_or_create(
        requester=users['user2'],
        pandit=users['pandit2'],
        defaults={
            'optional_requested_date': date.today() + timedelta(days=14),
            'optional_requested_time': time(11, 0),
            'message': 'Marriage ceremony booking intent',
            'status': BookingIntent.STATUS_VIEWED,
            'requester_status_at_creation': users['user2'].status,
            'pandit_status_at_creation': users['pandit2'].status,
        }
    )
    if created:
        print(f"  [OK] Created booking intent: {users['user2'].email} -> {users['pandit2'].email} (Viewed)")
    
    # User 3 → Pandit 1 (Submitted)
    intent3, created = BookingIntent.objects.get_or_create(
        requester=users['user3'],
        pandit=users['pandit1'],
        defaults={
            'optional_requested_date': date.today() + timedelta(days=21),
            'message': 'Satyanarayan Pooja required',
            'status': BookingIntent.STATUS_SUBMITTED,
            'requester_status_at_creation': users['user3'].status,
            'pandit_status_at_creation': users['pandit1'].status,
        }
    )
    if created:
        print(f"  [OK] Created booking intent: {users['user3'].email} -> {users['pandit1'].email} (Submitted)")
    
    # User 1 → Pandit 2 (Expired - older date)
    intent4, created = BookingIntent.objects.get_or_create(
        requester=users['user1'],
        pandit=users['pandit2'],
        defaults={
            'optional_requested_date': date.today() - timedelta(days=30),
            'optional_requested_time': time(9, 0),
            'message': 'Lakshmi Pooja for Diwali',
            'status': BookingIntent.STATUS_EXPIRED,
            'requester_status_at_creation': users['user1'].status,
            'pandit_status_at_creation': users['pandit2'].status,
        }
    )
    if created:
        print(f"  [OK] Created booking intent: {users['user1'].email} -> {users['pandit2'].email} (Expired)")
    
    # User 2 → Pandit 1 (Cancelled)
    intent5, created = BookingIntent.objects.get_or_create(
        requester=users['user2'],
        pandit=users['pandit1'],
        defaults={
            'optional_requested_date': date.today() + timedelta(days=5),
            'message': 'Cancelled booking',
            'status': BookingIntent.STATUS_CANCELLED,
            'requester_status_at_creation': users['user2'].status,
            'pandit_status_at_creation': users['pandit1'].status,
        }
    )
    if created:
        print(f"  [OK] Created booking intent: {users['user2'].email} -> {users['pandit1'].email} (Cancelled)")


def create_reviews(users):
    """Create reviews with various ratings for testing"""
    print("\n[REVIEWS] Creating Reviews...")
    
    # User 1 reviews Pandit 1 (5 stars)
    review1, created = Review.objects.get_or_create(
        user=users['user1'],
        pandit=users['pandit1'],
        defaults={
            'rating': 5,
            'review_text': 'Excellent service! Very professional and knowledgeable. Highly recommended.',
            'visibility_state': Review.VISIBLE,
            'reviewer_status_at_creation': users['user1'].status,
            'pandit_status_at_creation': users['pandit1'].status,
        }
    )
    if created:
        print(f"  [OK] Created review: {users['user1'].email} -> {users['pandit1'].email} (5 stars)")
    
    # User 2 reviews Pandit 2 (4 stars)
    review2, created = Review.objects.get_or_create(
        user=users['user2'],
        pandit=users['pandit2'],
        defaults={
            'rating': 4,
            'review_text': 'Good service, very punctual and respectful.',
            'visibility_state': Review.VISIBLE,
            'reviewer_status_at_creation': users['user2'].status,
            'pandit_status_at_creation': users['pandit2'].status,
        }
    )
    if created:
        print(f"  [OK] Created review: {users['user2'].email} -> {users['pandit2'].email} (4 stars)")
    
    # User 3 reviews Pandit 1 (5 stars)
    review3, created = Review.objects.get_or_create(
        user=users['user3'],
        pandit=users['pandit1'],
        defaults={
            'rating': 5,
            'review_text': 'Outstanding experience! The pooja was conducted with great devotion and attention to detail.',
            'visibility_state': Review.VISIBLE,
            'reviewer_status_at_creation': users['user3'].status,
            'pandit_status_at_creation': users['pandit1'].status,
        }
    )
    if created:
        print(f"  [OK] Created review: {users['user3'].email} -> {users['pandit1'].email} (5 stars)")
    
    # User 1 reviews Pandit 2 (4 stars)
    review4, created = Review.objects.get_or_create(
        user=users['user1'],
        pandit=users['pandit2'],
        defaults={
            'rating': 4,
            'review_text': 'Very satisfied with the service. Would recommend to others.',
            'visibility_state': Review.VISIBLE,
            'reviewer_status_at_creation': users['user1'].status,
            'pandit_status_at_creation': users['pandit2'].status,
        }
    )
    if created:
        print(f"  [OK] Created review: {users['user1'].email} -> {users['pandit2'].email} (4 stars)")


def main():
    """Main function to populate all dummy data"""
    print("=" * 60)
    print("[START] POPULATING DUMMY DATA FOR NITYA DHARMA")
    print("=" * 60)
    
    try:
        # Create master data
        cities, areas, poojas = create_master_data()
        
        # Create users
        users = create_users()
        
        # Create referral links
        referral_links = create_referral_links(users)
        
        # Create Pandit profiles
        profiles = create_pandit_profiles(users, cities, areas, poojas)
        
        # Create availability
        create_availability(users, profiles, cities, areas)
        
        # Create booking intents
        create_booking_intents(users)
        
        # Create reviews
        create_reviews(users)
        
        print("\n" + "=" * 60)
        print("[SUCCESS] DUMMY DATA POPULATION COMPLETE!")
        print("=" * 60)
        print("\n[SUMMARY]")
        print(f"  - Cities: {City.objects.count()}")
        print(f"  - Areas: {LocalArea.objects.count()}")
        print(f"  - Poojas: {Pooja.objects.count()}")
        print(f"  - Users: {User.objects.count()}")
        print(f"  - Referral Links: {ReferralLink.objects.count()}")
        print(f"  - Pandit Profiles: {PanditProfile.objects.count()}")
        print(f"  - Availability: {Availability.objects.count()}")
        print(f"  - Booking Intents: {BookingIntent.objects.count()}")
        print(f"  - Reviews: {Review.objects.count()}")
        print("\n[LOGIN CREDENTIALS]")
        print("  Super Admin: admin@nityadharma.com / admin123")
        print("  Admin Pandit: adminpandit@nityadharma.com / admin123")
        print("  Pandit 1: pandit1@nityadharma.com / pandit123")
        print("  Pandit 2: pandit2@nityadharma.com / pandit123")
        print("  User 1: user1@nityadharma.com / user123")
        print("  User 2: user2@nityadharma.com / user123")
        print("  User 3: user3@nityadharma.com / user123")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

