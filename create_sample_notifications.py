#!/usr/bin/env python
"""Create sample announcement and event for testing notifications."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings')
django.setup()

from pages.models import Page, PagePost
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from notifications.services import NotificationService

User = get_user_model()

# Get first active temple page
page = Page.objects.filter(page_type='TEMPLE', status='ACTIVE').first()
super_admin = User.objects.filter(is_superuser=True).first()

if not page:
    print("ERROR: No active temple page found. Please create a temple page first.")
    exit(1)

if not super_admin:
    print("ERROR: No super admin user found.")
    exit(1)

print(f"Using Temple: {page.title} (ID: {page.public_id})")
print(f"Using User: {super_admin.email}")

# Create Announcement
announcement = PagePost.objects.create(
    page=page,
    post_type='ANNOUNCEMENT',
    title='Special Pooja Event - All Devotees Welcome',
    content='We are pleased to announce a special pooja ceremony this Sunday. All devotees are requested to attend this auspicious event. The pooja will start at 9:00 AM sharp. Please arrive on time to receive blessings.',
    created_by=super_admin
)
print(f'\n✅ Created Announcement: {announcement.title}')

# Send notification for announcement
try:
    count = NotificationService.send_temple_notification(
        sender=super_admin,
        page=page,
        title=announcement.title,
        message=announcement.content[:200]
    )
    print(f'   📢 Sent {count} notifications for announcement')
except Exception as e:
    print(f'   ⚠️  Error sending notification: {e}')

# Create Event
event_date = datetime.now() + timedelta(days=7)
event = PagePost.objects.create(
    page=page,
    post_type='EVENT',
    title='Maha Abhishekam Event',
    content='Join us for a grand Maha Abhishekam ceremony. This is a rare opportunity to witness and participate in this sacred ritual. All are welcome to attend and receive divine blessings.',
    event_date=event_date,
    event_location='Main Temple Hall',
    created_by=super_admin
)
print(f'\n✅ Created Event: {event.title}')
print(f'   📅 Event Date: {event.event_date.strftime("%B %d, %Y at %I:%M %p")}')
print(f'   📍 Event Location: {event.event_location}')

# Send notification for event
try:
    event_info = []
    if event.event_date:
        event_info.append(f"Date: {event.event_date.strftime('%B %d, %Y at %I:%M %p')}")
    if event.event_location:
        event_info.append(f"Location: {event.event_location}")
    event_details = "\n".join(event_info)
    full_message = f"{event.content}\n\n{event_details}"
    
    count = NotificationService.send_temple_notification(
        sender=super_admin,
        page=page,
        title=event.title,
        message=full_message[:200]
    )
    print(f'   📢 Sent {count} notifications for event')
except Exception as e:
    print(f'   ⚠️  Error sending notification: {e}')

print('\n✅ Sample data created successfully!')
print(f'\n📋 Summary:')
print(f'   - Announcement: {announcement.title}')
print(f'   - Event: {event.title}')
print(f'\n🔗 View notifications at: http://localhost:8000/notifications/')



















