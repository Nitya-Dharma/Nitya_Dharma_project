"""
Contact Us System - Role-based reason configuration.
"""

CONTACT_REASONS = {
    "guest": [
        "Want to register as Pandit",
        "Temple listing request",
        "Partnership inquiry",
        "Media inquiry",
        "General inquiry"
    ],
    "end_user": [
        "Issue with booking",
        "Problem with a pandit",
        "Temple information incorrect",
        "Account issue",
        "General inquiry"
    ],
    "pandit": [
        "Profile update issue",
        "Approval delay",
        "Earnings clarification",
        "Document update request",
        "Technical issue"
    ],
    "admin_pandit": [
        "Escalate dispute",
        "Moderation clarification",
        "Policy question",
        "Temple management issue",
        "System issue"
    ],
    "super_admin": [
        "System configuration",
        "Internal inquiry"
    ]
}












