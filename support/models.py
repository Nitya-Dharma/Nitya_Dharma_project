"""
Contact Request Models
"""
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


class ContactRequest(models.Model):
    """
    Contact Request model for handling user inquiries.
    """
    
    ROLE_CHOICES = [
        ('guest', 'Guest'),
        ('end_user', 'End User'),
        ('pandit', 'Pandit'),
        ('admin_pandit', 'Admin Pandit'),
        ('super_admin', 'Super Admin'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_requests_submitted',
        help_text='User who submitted this contact request (null for guests)'
    )

    role_at_submission = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text='Role of the user at the time of submission'
    )

    email = models.EmailField(
        help_text='Contact email address'
    )

    mobile_number = models.CharField(
        max_length=15,
        help_text='Contact mobile number (mandatory)'
    )

    subject = models.CharField(
        max_length=255,
        help_text='Subject of the contact request'
    )

    message = models.TextField(
        help_text='Message content'
    )

    selected_reasons = models.JSONField(
        default=list,
        help_text='List of selected reasons for contact'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        help_text='Current status of the contact request'
    )

    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_contacts",
        help_text='Super Admin who is handling this request'
    )

    admin_reply = models.TextField(
        null=True,
        blank=True,
        help_text='Internal reply from Super Admin'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contact Request'
        verbose_name_plural = 'Contact Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['role_at_submission', '-created_at']),
        ]

    def __str__(self):
        return f"Contact Request from {self.email} - {self.subject} ({self.status})"
