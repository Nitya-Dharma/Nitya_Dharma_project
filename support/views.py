"""
Contact Us Views
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import ContactRequest

# Defaults preserved when settings are missing
_CONTACT_LIMIT_DEFAULT = 3
_CONTACT_WINDOW_DEFAULT = 300
from .constants import CONTACT_REASONS
from notifications.services import NotificationService
from notifications.constants import NOTIFICATION_TYPE_SYSTEM

User = get_user_model()
logger = logging.getLogger(__name__)


def get_user_role(user):
    """Get role string for user."""
    if not user.is_authenticated:
        return "guest"
    
    if user.is_superuser:
        return "super_admin"
    elif user.role == 'admin':
        return "admin_pandit"
    elif user.role == 'pandit':
        return "pandit"
    else:
        return "end_user"


def check_rate_limit(request):
    """
    Check if user has exceeded rate limit (default: 3 submissions per 5 minutes).
    Returns (is_allowed, time_remaining_seconds)
    """
    from core.config import get_config_value
    settings_default_count = getattr(settings, 'CONTACT_RATE_LIMIT_COUNT', _CONTACT_LIMIT_DEFAULT)
    settings_default_window = getattr(settings, 'CONTACT_RATE_LIMIT_WINDOW_SECONDS', _CONTACT_WINDOW_DEFAULT)
    limit = get_config_value('CONTACT_RATE_LIMIT_COUNT', settings_default_count)
    window = get_config_value('CONTACT_RATE_LIMIT_WINDOW_SECONDS', settings_default_window)
    session_key = f'contact_submissions_{request.META.get("REMOTE_ADDR", "unknown")}'
    submissions = request.session.get(session_key, [])
    
    now = timezone.now()
    recent_submissions = []
    for ts_str in submissions:
        try:
            if isinstance(ts_str, str):
                ts = timezone.datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            else:
                ts = ts_str
            if (now - ts).total_seconds() < window:
                recent_submissions.append(ts_str)
        except (ValueError, TypeError):
            continue
    
    if len(recent_submissions) >= limit:
        try:
            oldest_str = recent_submissions[0]
            if isinstance(oldest_str, str):
                oldest = timezone.datetime.fromisoformat(oldest_str.replace('Z', '+00:00'))
            else:
                oldest = oldest_str
            time_remaining = window - (now - oldest).total_seconds()
            return False, max(0, int(time_remaining))
        except (ValueError, TypeError):
            return False, 60
    
    return True, 0


def record_submission(request):
    """Record submission timestamp in session."""
    session_key = f'contact_submissions_{request.META.get("REMOTE_ADDR", "unknown")}'
    submissions = request.session.get(session_key, [])
    # Store as ISO format string
    submissions.append(timezone.now().isoformat())
    # Keep only last 10 submissions to prevent session bloat
    request.session[session_key] = submissions[-10:]
    request.session.modified = True


@require_http_methods(["GET", "POST"])
def contact_us(request):
    """
    Contact Us form view.
    Accessible to all users (including guests).
    """
    user = request.user
    role = get_user_role(user)
    allowed_reasons = CONTACT_REASONS.get(role, [])
    
    if request.method == "POST":
        # Rate limiting check
        is_allowed, time_remaining = check_rate_limit(request)
        if not is_allowed:
            messages.error(
                request,
                f"Too many submissions. Please wait {time_remaining} seconds before submitting again."
            )
            return render(request, 'support/contact_us.html', {
                'allowed_reasons': allowed_reasons,
                'role': role,
                'user': user,
            })
        
        # Get form data
        email = request.POST.get('email', '').strip()
        mobile_number = request.POST.get('mobile_number', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        selected_reasons = request.POST.getlist('selected_reasons')
        
        # Validation
        errors = []
        if not email:
            errors.append("Email is required.")
        if not mobile_number:
            errors.append("Mobile number is required.")
        if not subject:
            errors.append("Subject is required.")
        if not message:
            errors.append("Message is required.")
        if not selected_reasons:
            errors.append("Please select at least one reason.")
        
        # Validate selected reasons are in allowed list
        if selected_reasons:
            invalid_reasons = [r for r in selected_reasons if r not in allowed_reasons]
            if invalid_reasons:
                errors.append("Invalid reason selected.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'support/contact_us.html', {
                'allowed_reasons': allowed_reasons,
                'role': role,
                'user': user,
                'form_data': {
                    'email': email,
                    'mobile_number': mobile_number,
                    'subject': subject,
                    'message': message,
                    'selected_reasons': selected_reasons,
                }
            })
        
        # Create contact request
        try:
            with transaction.atomic():
                contact_request = ContactRequest.objects.create(
                    submitted_by=user if user.is_authenticated else None,
                    role_at_submission=role,
                    email=email,
                    mobile_number=mobile_number,
                    subject=subject,
                    message=message,
                    selected_reasons=selected_reasons,
                    status='new'
                )
                
                # Record submission for rate limiting
                record_submission(request)
                
                # Send notification to Super Admins + Admin Pandits (navbar badge + dashboards)
                from django.db.models import Q
                admin_users = User.objects.filter(
                    Q(is_superuser=True) | Q(role='admin'),
                    is_active=True
                ).distinct()
                for admin_user in admin_users:
                    try:
                        NotificationService.create_notification(
                            recipient=admin_user,
                            notification_type=NOTIFICATION_TYPE_SYSTEM,
                            source_module='support',
                            payload={
                                'message': f'New contact message from {role}.',
                                'contact_request_id': contact_request.id,
                                'role': role,
                            }
                        )
                    except Exception as e:
                        logger.error(f"Failed to send notification to admin {admin_user.id}: {e}")
                
                messages.success(
                    request,
                    "Thank you for contacting us! We'll get back to you soon."
                )
                return redirect('support:contact_us')
        
        except Exception as e:
            logger.error(f"Error creating contact request: {e}", exc_info=True)
            messages.error(
                request,
                "An error occurred while submitting your request. Please try again."
            )
    
    # SEO Meta for Contact Us page
    base_url = request.build_absolute_uri('/').rstrip('/')
    canonical_url = f"{base_url}/contact-us/"
    
    seo_context = {
        'allowed_reasons': allowed_reasons,
        'role': role,
        'user': user,
        'seo_title': 'Contact Us - Nitya Dharma | Get in Touch',
        'seo_description': 'Contact Nitya Dharma for inquiries about pandit services, temple listings, partnerships, or general questions. We\'re here to help you connect with trusted spiritual guides.',
        'seo_keywords': 'contact nitya dharma, pandit inquiry, temple listing, partnership inquiry, support',
        'canonical_url': canonical_url,
        'og_title': 'Contact Us - Nitya Dharma',
        'og_description': 'Get in touch with Nitya Dharma for inquiries about pandit services, temple listings, or general questions.',
        'og_type': 'website',
        'og_image': f"{base_url}{settings.STATIC_URL}images/og-contact.jpg" if hasattr(settings, 'STATIC_URL') else '',
    }
    
    return render(request, 'support/contact_us.html', seo_context)


@login_required
@require_http_methods(["GET", "POST"])
def contact_requests_admin(request):
    """
    Super Admin dashboard for managing contact requests.
    Only accessible to superusers.
    """
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super Admin only.")
        return redirect('core:home')
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    role_filter = request.GET.get('role', '')
    
    # Get all contact requests
    contact_requests = ContactRequest.objects.all()
    
    # Apply filters
    if status_filter:
        contact_requests = contact_requests.filter(status=status_filter)
    if role_filter:
        contact_requests = contact_requests.filter(role_at_submission=role_filter)
    
    # Handle status update (must be before queryset evaluation)
    if request.method == "POST":
        contact_id = request.POST.get('contact_id')
        action = request.POST.get('action')
        
        if contact_id and action:
            contact = get_object_or_404(ContactRequest, id=contact_id)
            
            if action == 'in_progress':
                contact.status = 'in_progress'
                contact.handled_by = request.user
                contact.save()
                messages.success(request, f"Contact request #{contact_id} marked as In Progress.")
            elif action == 'resolved':
                contact.status = 'resolved'
                contact.handled_by = request.user
                contact.save()
                messages.success(request, f"Contact request #{contact_id} marked as Resolved.")
            elif action == 'closed':
                contact.status = 'closed'
                contact.handled_by = request.user
                contact.save()
                messages.success(request, f"Contact request #{contact_id} marked as Closed.")
            elif action == 'reply':
                admin_reply = request.POST.get('admin_reply', '').strip()
                if admin_reply:
                    contact.admin_reply = admin_reply
                    contact.status = 'in_progress'
                    contact.handled_by = request.user
                    contact.save()
                    
                    # Optionally send notification to user if logged in
                    if contact.submitted_by:
                        try:
                            NotificationService.create_notification(
                                recipient=contact.submitted_by,
                                notification_type=NOTIFICATION_TYPE_SYSTEM,
                                source_module='support',
                                payload={
                                    'message': f'Reply to your contact request: {contact.subject}',
                                    'contact_request_id': contact.id,
                                }
                            )
                        except Exception as e:
                            logger.error(f"Failed to send notification to user {contact.submitted_by.id}: {e}")
                    
                    messages.success(request, f"Reply saved for contact request #{contact_id}.")
                else:
                    messages.error(request, "Reply cannot be empty.")
        
        # After POST, redirect to refresh the page and show updated data (preserve filters)
        redirect_url = 'support:contact_requests_admin'
        if status_filter:
            redirect_url += f'?status={status_filter}'
        if role_filter:
            redirect_url += f'&role={role_filter}' if status_filter else f'?role={role_filter}'
        return redirect(redirect_url)
    
    # Order by created date (newest first)
    contact_requests = contact_requests.order_by('-created_at')
    
    # Evaluate queryset to list to ensure it's properly passed to template
    contact_requests_list = list(contact_requests)
    
    # Debug: Log the count
    logger.info(f"Contact requests found: {len(contact_requests_list)}")
    if len(contact_requests_list) > 0:
        logger.info(f"First contact request: ID={contact_requests_list[0].id}, Email={contact_requests_list[0].email}")
    
    # Get counts for stats
    stats = {
        'total': ContactRequest.objects.count(),
        'new': ContactRequest.objects.filter(status='new').count(),
        'in_progress': ContactRequest.objects.filter(status='in_progress').count(),
        'resolved': ContactRequest.objects.filter(status='resolved').count(),
        'closed': ContactRequest.objects.filter(status='closed').count(),
    }
    
    return render(request, 'support/contact_requests_admin.html', {
        'contact_requests': contact_requests_list,
        'contact_requests_count': len(contact_requests_list),
        'stats': stats,
        'status_filter': status_filter,
        'role_filter': role_filter,
        'dashboard_has_data': True,  # Required by dashboard_base.html to show content
    })
