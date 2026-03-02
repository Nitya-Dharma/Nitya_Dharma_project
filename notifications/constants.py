"""
Notification Constants

Task 17.2: Notification Types Classification

Defines notification type choices for the Notification model.
These are descriptive only - no priority, no business logic.
"""

# Notification Type Constants (used in services.py)
NOTIFICATION_TYPE_SYSTEM = 'system'
NOTIFICATION_TYPE_GOVERNANCE = 'governance'
NOTIFICATION_TYPE_PAGE_UPDATE = 'page_update'
NOTIFICATION_TYPE_BOOKING_INTENT = 'booking_intent'
NOTIFICATION_TYPE_REVIEW = 'review'
NOTIFICATION_TYPE_PAGE_MODERATOR_ASSIGNED = 'page_moderator_assigned'
NOTIFICATION_TYPE_TEMPLE_ANNOUNCEMENT = 'temple_announcement'

# Notification Type Choices (for model CharField choices)
# Format: (value, human-readable label)
NOTIFICATION_TYPE_CHOICES = [
    # System Notifications (mandatory, cannot be disabled)
    (NOTIFICATION_TYPE_SYSTEM, 'System Notification'),
    
    # Governance Notifications (mandatory, cannot be disabled)
    (NOTIFICATION_TYPE_GOVERNANCE, 'Governance Notification'),
    
    # Page Update Notifications (optional, can be disabled)
    (NOTIFICATION_TYPE_PAGE_UPDATE, 'Page Update Notification'),
    
    # Booking Intent Notifications (optional, can be disabled)
    (NOTIFICATION_TYPE_BOOKING_INTENT, 'Booking Intent Notification'),
    
    # Review Notifications (optional, can be disabled)
    (NOTIFICATION_TYPE_REVIEW, 'Review Notification'),
    
    # Page Moderator Assigned (optional, can be disabled)
    (NOTIFICATION_TYPE_PAGE_MODERATOR_ASSIGNED, 'Page Moderator Assigned'),
    
    # Temple Announcement Notifications (optional, can be disabled)
    (NOTIFICATION_TYPE_TEMPLE_ANNOUNCEMENT, 'Temple Announcement'),
]
