"""
Notification UI views (template-based).

Task 17.UI: Notification UI (Template-based)
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from .models import Notification
try:
    from .services import NotificationService
except ImportError:
    NotificationService = None

logger = logging.getLogger(__name__)

# Base filter for non-expired notifications (same as navbar context processor)
def _non_expired_filter():
    return Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())


@login_required
def notifications_list(request):
    """
    User notifications list page (HTML template).
    Shows only the logged-in user's notifications.
    Badge clears only when user explicitly marks notification(s) as read.
    """
    # Single queryset: same recipient and expiry logic as navbar count
    notifications_qs = (
        Notification.objects.filter(recipient=request.user)
        .filter(_non_expired_filter())
        .order_by('-created_at')
    )

    # Optional type filter (users / pandits / temples) to match admin tabs
    notification_type = (request.GET.get('type') or '').strip().lower()
    if notification_type == 'users':
        notifications_qs = notifications_qs.filter(
            Q(source_module='booking_intent') | Q(source_module='reviews') |
            Q(source_module='support') |
            Q(notification_type='booking_intent') | Q(notification_type='review')
        )
    elif notification_type == 'pandits':
        notifications_qs = notifications_qs.filter(
            Q(source_module='accounts') | Q(source_module='profiles') | Q(source_module='governance') | Q(notification_type='governance')
        ).exclude(
            Q(source_module='booking_intent') | Q(source_module='reviews') | Q(source_module='pages') | Q(source_module='support')
        )
    elif notification_type == 'temples':
        notifications_qs = notifications_qs.filter(
            Q(source_module='pages') | Q(notification_type='page_update') | Q(notification_type='temple_announcement')
        )

    notifications = list(notifications_qs[:50])
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).filter(_non_expired_filter()).count()

    logger.info(
        "Notification fetch",
        extra={
            "user_id": request.user.id,
            "total": len(notifications),
            "unread": unread_count,
        }
    )

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'user': request.user,
    }
    return render(request, 'notifications/notifications_list.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """
    Mark a single notification as read.
    
    Redirects back to appropriate notifications list based on user role.
    """
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    
    # Get redirect URL from request (if provided) or determine based on role
    redirect_url = request.GET.get('next', None)
    
    if NotificationService:
        if NotificationService.mark_as_read(notification, request.user):
            messages.success(request, 'Notification marked as read.')
        else:
            messages.error(request, 'Failed to mark notification as read.')
    else:
        # Fallback: direct update
        from django.utils import timezone
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        messages.success(request, 'Notification marked as read.')
    
    # Contact/support notification: redirect to Contact Requests admin
    if notification.source_module == 'support':
        return redirect('support:contact_requests_admin')
    # Check if this is a page moderator assigned notification
    if notification.notification_type == 'page_moderator_assigned':
        # Redirect to Pandit Dashboard with Temple Pages tab
        if request.user.role == 'pandit':
            return redirect('module5_dashboards:dashboard_pandit' + '#temple-pages-tab')
        else:
            return redirect('notifications:list')
    
    # TEMPLE-SCOPED NOTIFICATION: Handle temple announcement notification clicks
    if notification.notification_type == 'temple_announcement' and notification.page:
        # Redirect to temple page
        from pages.models import Page
        try:
            return redirect('pages:page_detail', page_public_id=notification.page.public_id)
        except Exception:
            pass  # Fallback to notifications list if redirect fails
    
    # Redirect to appropriate page
    if redirect_url:
        return redirect(redirect_url)
    elif request.user.is_superuser or request.user.role == 'admin':
        return redirect('accounts:admin_notification_list', user_id=request.user.id)
    else:
        return redirect('notifications:list')


@login_required
def mark_all_read(request):
    """
    Mark all unread notifications as read for the current user.
    
    Redirects back to notifications list.
    """
    if NotificationService:
        count = NotificationService.mark_all_as_read(request.user)
    else:
        # Fallback: direct update
        from django.utils import timezone
        from django.db.models import Q
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        ).update(is_read=True, read_at=timezone.now())
    
    if count > 0:
        messages.success(request, f'{count} notification(s) marked as read.')
    else:
        messages.info(request, 'No unread notifications.')
    
    return redirect('notifications:list')
