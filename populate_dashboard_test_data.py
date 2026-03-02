"""
Script to populate additional dummy booking intents and reviews for dashboard testing.

This script adds more diverse data to test:
- Dashboard metrics (various statuses)
- Recent activity section (different dates)
- Multiple booking intents per user
- Multiple reviews per user

Run this script after populate_dummy_data.py:
    python populate_dashboard_test_data.py
"""

import os
import django
from datetime import date, time, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
django.setup()

from accounts.models import User
from booking_intent.models import BookingIntent
from reviews.models import Review


def populate_dashboard_test_data():
    """Add additional booking intents and reviews for dashboard testing"""
    print("\n[DASHBOARD TEST DATA] Populating Additional Booking Intents and Reviews...")
    
    # Get users
    try:
        user1 = User.objects.get(email='user1@nityadharma.com')
        user2 = User.objects.get(email='user2@nityadharma.com')
        user3 = User.objects.get(email='user3@nityadharma.com')
        pandit1 = User.objects.get(email='pandit1@nityadharma.com')
        pandit2 = User.objects.get(email='pandit2@nityadharma.com')
        pandit3 = User.objects.get(email='pandit3@nityadharma.com')
        pandit4 = User.objects.get(email='pandit4@nityadharma.com')
    except User.DoesNotExist as e:
        print(f"  [ERROR] User not found: {e}")
        print("  [INFO] Please run populate_dummy_data.py first")
        return
    
    # Get all active pandits
    all_pandits = User.objects.filter(role='pandit', status='active', is_active=True)
    if not all_pandits.exists():
        print("  [ERROR] No active pandits found. Please run populate_dummy_data.py first")
        return
    
    print(f"  [INFO] Found {all_pandits.count()} active pandits")
    print(f"  [INFO] Found 3 test users")
    
    # Additional booking intents for user1 (to test multiple intents)
    print("\n  [BOOKING INTENTS] Creating additional booking intents...")
    
    booking_intents_data = [
        # User 1 - More intents
        {
            'requester': user1,
            'pandit': pandit3,
            'optional_requested_date': date.today() + timedelta(days=3),
            'optional_requested_time': time(14, 0),
            'message': 'Need Navagraha Pooja for upcoming festival',
            'status': BookingIntent.STATUS_SUBMITTED,
            'created_at': timezone.now() - timedelta(days=2),
        },
        {
            'requester': user1,
            'pandit': pandit4,
            'optional_requested_date': date.today() + timedelta(days=10),
            'message': 'Satyanarayana Vratam required',
            'status': BookingIntent.STATUS_VIEWED,
            'created_at': timezone.now() - timedelta(days=1),
        },
        {
            'requester': user1,
            'pandit': pandit1,
            'optional_requested_date': date.today() + timedelta(days=15),
            'optional_requested_time': time(16, 0),
            'message': 'Lakshmi Pooja for new business',
            'status': BookingIntent.STATUS_SUBMITTED,
            'created_at': timezone.now() - timedelta(hours=6),
        },
        # User 2 - More intents
        {
            'requester': user2,
            'pandit': pandit3,
            'optional_requested_date': date.today() + timedelta(days=7),
            'message': 'Durga Pooja booking',
            'status': BookingIntent.STATUS_VIEWED,
            'created_at': timezone.now() - timedelta(days=3),
        },
        {
            'requester': user2,
            'pandit': pandit1,
            'optional_requested_date': date.today() + timedelta(days=20),
            'optional_requested_time': time(10, 30),
            'message': 'Hanuman Pooja for strength and protection',
            'status': BookingIntent.STATUS_SUBMITTED,
            'created_at': timezone.now() - timedelta(hours=12),
        },
        # User 3 - More intents
        {
            'requester': user3,
            'pandit': pandit2,
            'optional_requested_date': date.today() + timedelta(days=5),
            'message': 'Rudrabhishekam for spiritual growth',
            'status': BookingIntent.STATUS_SUBMITTED,
            'created_at': timezone.now() - timedelta(days=4),
        },
        {
            'requester': user3,
            'pandit': pandit4,
            'optional_requested_date': date.today() + timedelta(days=12),
            'optional_requested_time': time(15, 0),
            'message': 'Bhoomi Puja for new property',
            'status': BookingIntent.STATUS_VIEWED,
            'created_at': timezone.now() - timedelta(hours=3),
        },
    ]
    
    created_intents = 0
    skipped_intents = 0
    
    for intent_data in booking_intents_data:
        # Check if intent already exists (by requester, pandit, and similar date)
        existing = BookingIntent.objects.filter(
            requester=intent_data['requester'],
            pandit=intent_data['pandit'],
            optional_requested_date=intent_data.get('optional_requested_date')
        ).first()
        
        if existing:
            skipped_intents += 1
            continue
        
        # Extract created_at if provided
        created_at = intent_data.pop('created_at', None)
        
        # Create the intent
        intent = BookingIntent.objects.create(
            requester_status_at_creation=intent_data['requester'].status,
            pandit_status_at_creation=intent_data['pandit'].status,
            **intent_data
        )
        
        # Update created_at if specified
        if created_at:
            BookingIntent.objects.filter(id=intent.id).update(created_at=created_at)
        
        created_intents += 1
        print(f"    [OK] Created booking intent: {intent_data['requester'].email} -> {intent_data['pandit'].email} ({intent_data['status']})")
    
    print(f"  [SUMMARY] Created {created_intents} new booking intents, skipped {skipped_intents} duplicates")
    
    # Additional reviews for users (to test multiple reviews)
    print("\n  [REVIEWS] Creating additional reviews...")
    
    reviews_data = [
        # User 1 - More reviews
        {
            'user': user1,
            'pandit': pandit3,
            'rating': 5,
            'review_text': 'Exceptional service! Very knowledgeable and professional. The pooja was conducted with great devotion.',
            'visibility_state': Review.VISIBLE,
            'created_at': timezone.now() - timedelta(days=5),
        },
        {
            'user': user1,
            'pandit': pandit4,
            'rating': 4,
            'review_text': 'Good experience overall. Punctual and respectful. Would recommend.',
            'visibility_state': Review.VISIBLE,
            'created_at': timezone.now() - timedelta(days=3),
        },
        # User 2 - More reviews
        {
            'user': user2,
            'pandit': pandit3,
            'rating': 5,
            'review_text': 'Outstanding pandit! Very detailed explanations and excellent service.',
            'visibility_state': Review.VISIBLE,
            'created_at': timezone.now() - timedelta(days=6),
        },
        {
            'user': user2,
            'pandit': pandit1,
            'rating': 4,
            'review_text': 'Satisfactory service. Good communication and timely completion.',
            'visibility_state': Review.VISIBLE,
            'created_at': timezone.now() - timedelta(hours=8),
        },
        # User 3 - More reviews
        {
            'user': user3,
            'pandit': pandit2,
            'rating': 5,
            'review_text': 'Amazing experience! Very spiritual and authentic. Highly recommended.',
            'visibility_state': Review.VISIBLE,
            'created_at': timezone.now() - timedelta(days=7),
        },
        {
            'user': user3,
            'pandit': pandit4,
            'rating': 4,
            'review_text': 'Good service. Professional and courteous. Would use again.',
            'visibility_state': Review.VISIBLE,
            'created_at': timezone.now() - timedelta(hours=2),
        },
    ]
    
    created_reviews = 0
    skipped_reviews = 0
    
    for review_data in reviews_data:
        # Check if review already exists (unique constraint on user + pandit)
        existing = Review.objects.filter(
            user=review_data['user'],
            pandit=review_data['pandit']
        ).first()
        
        if existing:
            skipped_reviews += 1
            continue
        
        # Extract created_at if provided
        created_at = review_data.pop('created_at', None)
        
        # Create the review
        review = Review.objects.create(
            reviewer_status_at_creation=review_data['user'].status,
            pandit_status_at_creation=review_data['pandit'].status,
            **review_data
        )
        
        # Update created_at if specified
        if created_at:
            Review.objects.filter(id=review.id).update(created_at=created_at)
        
        created_reviews += 1
        print(f"    [OK] Created review: {review_data['user'].email} -> {review_data['pandit'].email} ({review_data['rating']} stars)")
    
    print(f"  [SUMMARY] Created {created_reviews} new reviews, skipped {skipped_reviews} duplicates")
    
    # Final statistics
    print("\n[DASHBOARD TEST DATA] Final Statistics:")
    print(f"  - Total Booking Intents: {BookingIntent.objects.count()}")
    print(f"  - Total Reviews: {Review.objects.count()}")
    print(f"  - User 1 Booking Intents: {BookingIntent.objects.filter(requester=user1).count()}")
    print(f"  - User 1 Reviews: {Review.objects.filter(user=user1).count()}")
    print(f"  - User 2 Booking Intents: {BookingIntent.objects.filter(requester=user2).count()}")
    print(f"  - User 2 Reviews: {Review.objects.filter(user=user2).count()}")
    print(f"  - User 3 Booking Intents: {BookingIntent.objects.filter(requester=user3).count()}")
    print(f"  - User 3 Reviews: {Review.objects.filter(user=user3).count()}")
    
    print("\n[SUCCESS] Dashboard test data populated successfully!")
    print("\n[INFO] You can now test the dashboard at:")
    print("  - User Dashboard: http://127.0.0.1:8000/dashboard/user/")
    print("  - Booking Intents History: http://127.0.0.1:8000/booking-intent/history/")


if __name__ == '__main__':
    populate_dashboard_test_data()

