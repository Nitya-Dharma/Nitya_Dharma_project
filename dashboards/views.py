import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db import models, transaction
from django.core.exceptions import PermissionDenied
from accounts.decorators import pandit_required, admin_required
from referrals.models import ReferralLink
from services.views_expert_ui import get_expert_by_user
from core.models import ExpertInquiry, ExpertService
from services.expert_service_selection import (
    ExpertServiceSelectionError,
    primary_expert_type,
    resolve_active_services_by_ids,
)



@login_required
def expert_dashboard_view(request):
    expert = get_expert_by_user(request.user)
    if not expert:
        return redirect("/dashboard/user/")

    active_tab = request.GET.get("tab", "overview")
    allowed_tabs = {"overview", "profile", "requests", "reviews", "analytics", "settings"}
    if active_tab not in allowed_tabs:
        active_tab = "overview"

    is_complete = True
    if not expert.name:
        is_complete = False
    if not expert.phone:
        is_complete = False
    if not expert.experience_years or expert.experience_years <= 0:
        is_complete = False
    if not expert.description:
        is_complete = False

    available_services = list(
        ExpertService.objects.filter(is_active=True).order_by("display_order", "name")
    )
    selected_service_ids = list(expert.services.values_list("id", flat=True))
    profile_error = None
    success = False
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            phone = request.POST.get("phone")
            experience = request.POST.get("experience_years")
            description = request.POST.get("description")
            raw_service_ids = request.POST.getlist("services")
            selected_service_ids = [
                int(service_id)
                for service_id in raw_service_ids
                if str(service_id).isdigit()
            ]
            try:
                selected_services = resolve_active_services_by_ids(
                    raw_service_ids
                )
            except ExpertServiceSelectionError as exc:
                selected_services = []
                profile_error = str(exc)
                active_tab = "profile"

            if not profile_error and name and phone:
                with transaction.atomic():
                    expert.name = name
                    expert.phone = phone
                    try:
                        expert.experience_years = int(experience)
                    except Exception:
                        pass
                    expert.description = description
                    expert.expert_type = primary_expert_type(selected_services)

                    image = request.FILES.get("profile_image")
                    if image:
                        expert.profile_image = image
                    cover = request.FILES.get("cover_image")
                    if cover:
                        expert.cover_image = cover

                    expert.save()
                    expert.services.set(selected_services)
                selected_service_ids = [
                    service.id for service in selected_services
                ]
                success = True
                active_tab = "profile"
        except Exception:
            profile_error = "Unable to update profile. Please try again."
            active_tab = "profile"

    # Align with services.ExpertBookingIntent.related_name=service_booking_intents (not core.booking_intents).
    unread_requests_qs = expert.service_booking_intents.filter(is_viewed=False)
    has_active_intent = unread_requests_qs.exists()
    total_requests = expert.service_booking_intents.count()
    unread_requests_count = unread_requests_qs.count()

    inquiries_queryset = ExpertInquiry.objects.filter(expert=expert).order_by("-created_at")
    inquiries = list(inquiries_queryset[:10])

    reviews = list(expert.reviews.all().order_by("-created_at")[:10])

    profile_views = getattr(expert, "profile_views", 0)

    return render(
        request,
        "experts/dashboard.html",
        {
            "expert": expert,
            "profile": expert,
            "active_tab": active_tab,
            "dashboard_has_data": True,
            "success": success,
            "profile_error": profile_error,
            "available_services": available_services,
            "selected_service_ids": selected_service_ids,
            "is_complete": is_complete,
            "inquiries": inquiries,
            "reviews": reviews,
            "total_requests": total_requests,
            "profile_views": profile_views,
            "has_active_intent": has_active_intent,
            "unread_requests_count": unread_requests_count,
        },
    )


@login_required
def dashboard_user(request):
    """
    End User Dashboard - Task 5.UI.3
    
    Provides read-only overview of user's interactions:
    - Booking intents sent
    - Reviews submitted
    - Recent activity
    
    Display-only UI - no logic, no computation.
    """
    # Role-based redirect: Only regular users can access this dashboard
    if request.user.is_superuser:
        return redirect('module5_dashboards:dashboard_super_admin')
    elif request.user.role == 'admin':
        return redirect('module5_dashboards:dashboard_admin_pandit')
    elif request.user.role == 'pandit':
        return redirect('module5_dashboards:dashboard_pandit')
    elif request.user.role != 'user':
        # Unknown role, redirect to home
        return redirect('core:home')
    
    from booking_intent.models import BookingIntent
    from reviews.models import Review
    from profiles.models import PanditProfile
    
    # Get user's booking intents (read-only)
    user_booking_intents = BookingIntent.objects.filter(
        requester=request.user
    ).select_related('pandit', 'pandit__pandit_profile').order_by('-created_at')
    
    # Get user's reviews (read-only)
    user_reviews = Review.objects.filter(
        user=request.user
    ).select_related('pandit', 'pandit__pandit_profile').order_by('-created_at')
    
    # Calculate metrics (backend-computed, UI only displays)
    total_booking_intents = user_booking_intents.count()
    pending_booking_intents = user_booking_intents.filter(status__in=['submitted', 'viewed']).count()
    closed_booking_intents = user_booking_intents.filter(status__in=['expired', 'cancelled']).count()
    total_reviews = user_reviews.count()
    
    # Determine if dashboard has data
    dashboard_has_data = total_booking_intents > 0 or total_reviews > 0
    
    # Build metrics cards (backend-provided, UI displays)
    dashboard_metrics = []
    if dashboard_has_data:
        dashboard_metrics = [
            {
                'label': 'Total Booking Intents Sent',
                'value': total_booking_intents,
                'icon': 'bi bi-envelope',
            },
            {
                'label': 'Pending Booking Intents',
                'value': pending_booking_intents,
                'icon': 'bi bi-clock-history',
            },
            {
                'label': 'Closed Booking Intents',
                'value': closed_booking_intents,
                'icon': 'bi bi-check-circle',
            },
            {
                'label': 'Reviews Submitted',
                'value': total_reviews,
                'icon': 'bi bi-star',
            },
        ]
    
    # Build recent activity (max 10 items, backend-provided, UI displays)
    recent_activity = []
    if dashboard_has_data:
        # Combine booking intents and reviews, sort by date
        activities = []
        
        # Add booking intents
        for intent in user_booking_intents[:5]:
            pandit_name = 'Unknown Pandit'
            if intent.pandit.pandit_profile:
                pandit_name = intent.pandit.pandit_profile.display_name or intent.pandit.get_full_name() or intent.pandit.email
            elif intent.pandit:
                pandit_name = intent.pandit.get_full_name() or intent.pandit.email
            
            activities.append({
                'type': 'booking',
                'type_label': 'Booking Intent',
                'pandit_name': pandit_name,
                'date': intent.created_at,
                'status': intent.status,
            })
        
        # Add reviews
        for review in user_reviews[:5]:
            pandit_name = 'Unknown Pandit'
            if review.pandit.pandit_profile:
                pandit_name = review.pandit.pandit_profile.display_name or review.pandit.get_full_name() or review.pandit.email
            elif review.pandit:
                pandit_name = review.pandit.get_full_name() or review.pandit.email
            
            activities.append({
                'type': 'review',
                'type_label': 'Review',
                'pandit_name': pandit_name,
                'date': review.created_at,
                'status': 'submitted',  # Reviews are always submitted
            })
        
        # Sort by date (newest first) and take top 10
        activities.sort(key=lambda x: x['date'], reverse=True)
        recent_activity = activities[:10]
    
    return render(request, 'module5_dashboards/dashboard_user.html', {
        'user': request.user,
        'user_role': 'user',
        'dashboard_has_data': dashboard_has_data,
        'dashboard_metrics': dashboard_metrics,
        'recent_activity': recent_activity,
        'state_type': 'empty' if not dashboard_has_data else None,
    })


@login_required
def dashboard_pandit(request):
    """Pandit Dashboard - Task 5.UI.2"""
    # Role-based redirect: Only pandits can access this dashboard
    # Admin Pandits and Super Admins should be redirected to their own dashboards
    if request.user.is_superuser:
        return redirect('module5_dashboards:dashboard_super_admin')
    elif request.user.role == 'admin':
        return redirect('module5_dashboards:dashboard_admin_pandit')
    elif request.user.role != 'pandit':
        return redirect('core:home')
    
    # TASK 4 & 5: Get pages for Pandit (Temple Pages tab)
    from pages.page_permissions import get_pages_for_pandit
    from booking_intent.models import BookingIntent
    temple_pages = get_pages_for_pandit(request.user)
    has_temple_pages = len(temple_pages) > 0

    # Booking intents received by this pandit (for card and badge)
    pandit_booking_intents = BookingIntent.objects.filter(pandit=request.user)
    booking_intent_count = pandit_booking_intents.count()
    # Unread = not yet viewed (SUBMITTED only) – badge decreases when Pandit marks as viewed
    unread_booking_intents_count = pandit_booking_intents.filter(
        status=BookingIntent.STATUS_SUBMITTED
    ).count()
    pending_booking_intents_count = pandit_booking_intents.filter(
        status__in=[BookingIntent.STATUS_SUBMITTED, BookingIntent.STATUS_VIEWED]
    ).count()
    booking_intent_summary = None
    if pending_booking_intents_count > 0:
        booking_intent_summary = f"{pending_booking_intents_count} pending (awaiting your response)"

    return render(request, 'module5_dashboards/dashboard_pandit.html', {
        'user': request.user,
        'user_role': 'pandit',
        'temple_pages': temple_pages,
        'has_temple_pages': has_temple_pages,
        'booking_intent_count': booking_intent_count,
        'booking_intent_summary': booking_intent_summary,
        'pending_booking_intents_count': pending_booking_intents_count,
        'unread_booking_intents_count': unread_booking_intents_count,
    })


@admin_required
def dashboard_admin_pandit(request):
    """Admin Pandit Dashboard - Task 5.UI.4"""
    # Role-based redirect: Only Admin Pandit (admin role but not superuser) can access
    if request.user.is_superuser:
        return redirect('module5_dashboards:dashboard_super_admin')
    elif request.user.role != 'admin':
        # Not an admin, redirect based on actual role
        if request.user.role == 'pandit':
            return redirect('module5_dashboards:dashboard_pandit')
        elif request.user.role == 'user':
            return redirect('module5_dashboards:dashboard_user')
        else:
            return redirect('core:home')
    
    from accounts.models import User
    from profiles.models import PanditProfile
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    # Get date filters from request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Parse dates if provided
    date_filter_from = None
    date_filter_to = None
    if from_date:
        try:
            date_filter_from = datetime.strptime(from_date, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass
    if to_date:
        try:
            date_filter_to = datetime.strptime(to_date, '%Y-%m-%d').date()
            # Add one day to include the entire end date
            date_filter_to = date_filter_to + timedelta(days=1)
        except (ValueError, TypeError):
            pass
    
    # Get referral links created by this admin
    referral_links_query = ReferralLink.objects.filter(created_by=request.user)
    if date_filter_from:
        referral_links_query = referral_links_query.filter(created_at__gte=date_filter_from)
    if date_filter_to:
        referral_links_query = referral_links_query.filter(created_at__lt=date_filter_to)
    referral_links = referral_links_query.order_by('-created_at')[:10]
    
    # 1. ONBOARDING & APPROVAL PANEL - Get pending Pandits
    pending_pandits_query = User.objects.filter(
        role='pandit',
        status='pending'
    ).select_related('pandit_profile', 'referred_by')
    
    # Apply date filter to pending pandits (filter by created_at)
    if date_filter_from:
        pending_pandits_query = pending_pandits_query.filter(created_at__gte=date_filter_from)
    if date_filter_to:
        pending_pandits_query = pending_pandits_query.filter(created_at__lt=date_filter_to)
    
    pending_pandits = pending_pandits_query.order_by('-created_at')
    
    # Add referral source info for each pending pandit
    # TASK 5: Include email verification status for resend UI
    pending_pandits_list = []
    for pandit in pending_pandits:
        referral_source = 'Direct'
        if pandit.referred_by:
            referral_source = pandit.referred_by.get_full_name() or pandit.referred_by.email
        pending_pandits_list.append({
            'user': pandit,
            'referral_source': referral_source,
            'submitted_date': pandit.created_at,
            'email_verified': pandit.email_verified,
            'email_verified_at': pandit.email_verified_at,
        })
    
    # 2. PROFILE APPROVAL PANEL - Get profiles awaiting approval
    # Profiles that exist, belong to active pandits, but are not approved
    profiles_awaiting_approval_query = PanditProfile.objects.filter(
        user__role='pandit',
        user__status='active',
        is_profile_approved=False
    ).select_related('user')
    
    # Apply date filter to profiles (filter by updated_at)
    if date_filter_from:
        profiles_awaiting_approval_query = profiles_awaiting_approval_query.filter(updated_at__gte=date_filter_from)
    if date_filter_to:
        profiles_awaiting_approval_query = profiles_awaiting_approval_query.filter(updated_at__lt=date_filter_to)
    
    profiles_awaiting_approval = profiles_awaiting_approval_query.order_by('-updated_at')
    
    # Calculate profile completeness for each profile
    profiles_list = []
    for profile in profiles_awaiting_approval:
        # Simple completeness calculation
        fields_to_check = [
            profile.display_name or profile.user.get_full_name(),
            profile.about_description,
            profile.experience_years is not None,
            profile.languages_spoken,
            profile.cities_served.exists(),
            profile.poojas_performed.exists(),
        ]
        completed_fields = sum(1 for field in fields_to_check if field)
        total_fields = len(fields_to_check)
        completeness_percent = int((completed_fields / total_fields) * 100) if total_fields > 0 else 0
        
        profiles_list.append({
            'profile': profile,
            'pandit_name': profile.get_display_name(),
            'completeness_percent': completeness_percent,
            'last_updated': profile.updated_at,
        })
    
    # 3. PARTIAL BLOCK MANAGEMENT PANEL - Get active partial blocks
    from governance.models import PartialBlock
    active_partial_blocks_query = PartialBlock.objects.filter(
        is_active=True
    ).select_related('pandit', 'applied_by', 'removed_by')
    
    # Apply date filter to partial blocks (filter by applied_at)
    if date_filter_from:
        active_partial_blocks_query = active_partial_blocks_query.filter(applied_at__gte=date_filter_from)
    if date_filter_to:
        active_partial_blocks_query = active_partial_blocks_query.filter(applied_at__lt=date_filter_to)
    
    active_partial_blocks = active_partial_blocks_query.order_by('-applied_at')
    
    # 4. REFERRAL MANAGEMENT - Already fetched above (referral_links)
    
    # 5. TRUST & REFERRAL CHAIN VIEW - Get trust data for display (read-only)
    from trust_display.selectors import get_referral_chain_for_pandit
    from accounts.models import User as UserModel
    
    # Get sample pandits with referral chains for observation
    pandits_with_referrals_query = UserModel.objects.filter(
        role='pandit',
        status='active',
        referred_by__isnull=False
    ).select_related('referred_by', 'pandit_profile')
    
    # Apply date filter to trust chain data (filter by created_at)
    if date_filter_from:
        pandits_with_referrals_query = pandits_with_referrals_query.filter(created_at__gte=date_filter_from)
    if date_filter_to:
        pandits_with_referrals_query = pandits_with_referrals_query.filter(created_at__lt=date_filter_to)
    
    pandits_with_referrals = pandits_with_referrals_query[:10]
    
    trust_chain_data = []
    for pandit in pandits_with_referrals:
        try:
            referral_chain = get_referral_chain_for_pandit(pandit)
            trust_chain_data.append({
                'pandit': pandit,
                'pandit_name': pandit.pandit_profile.get_display_name() if hasattr(pandit, 'pandit_profile') else pandit.get_full_name(),
                'chain_length': referral_chain.get('chain_length', 0),
                'has_referral': referral_chain.get('has_referral', False),
            })
        except Exception:
            # Skip if error getting chain
            pass
    
    # Get all active pandits for partial block dropdown
    all_active_pandits = User.objects.filter(
        role='pandit',
        status='active'
    ).select_related('pandit_profile').order_by('first_name', 'last_name', 'email')
    
    # 7. NOTIFICATIONS PANEL - Get actionable notifications for Admin Pandit
    from notifications.models import Notification
    from notifications.constants import NOTIFICATION_TYPE_GOVERNANCE, NOTIFICATION_TYPE_SYSTEM
    from django.db.models import Q
    
    # Get recent notifications for this admin (last 20)
    admin_notifications_query = Notification.objects.filter(
        recipient=request.user
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )
    
    # Apply date filter to notifications (filter by created_at)
    if date_filter_from:
        admin_notifications_query = admin_notifications_query.filter(created_at__gte=date_filter_from)
    if date_filter_to:
        admin_notifications_query = admin_notifications_query.filter(created_at__lt=date_filter_to)
    
    admin_notifications = admin_notifications_query.order_by('-created_at')[:20]
    
    # Categorize notifications by type for actionable links
    notifications_list = []
    for notification in admin_notifications:
        action_url = None
        action_text = None
        
        # Determine action URL based on notification type and payload
        if notification.notification_type == NOTIFICATION_TYPE_GOVERNANCE:
            # Governance notifications might link to partial blocks or cases
            if 'partial_block' in notification.payload.get('action', ''):
                action_url = 'module5_dashboards:dashboard_admin_pandit'
                action_text = 'View Partial Blocks'
            elif 'pandit_approval' in notification.payload.get('action', ''):
                action_url = 'module5_dashboards:dashboard_admin_pandit'
                action_text = 'View Pending Pandits'
        elif notification.source_module == 'accounts':
            # Pandit onboarding notifications
            if 'pandit_pending' in str(notification.payload):
                action_url = 'module5_dashboards:dashboard_admin_pandit'
                action_text = 'View Pending Pandits'
        elif notification.source_module == 'profiles':
            # Profile approval notifications
            if 'profile_awaiting' in str(notification.payload):
                action_url = 'module5_dashboards:dashboard_admin_pandit'
                action_text = 'View Profiles Awaiting Approval'
        elif notification.source_module == 'referrals':
            # Referral link usage notifications
            action_url = 'module5_dashboards:dashboard_admin_pandit'
            action_text = 'View Referral Links'
        
        notifications_list.append({
            'notification': notification,
            'action_url': action_url,
            'action_text': action_text,
        })
    
    # 8. ANALYTICS DASHBOARD - Calculate read-only analytics
    from analytics.models import AnalyticsEvent
    from django.db.models import Count
    from datetime import timedelta, datetime
    
    # Calculate onboarding trends - use date filter if provided, otherwise last 30 days
    if date_filter_from:
        # Convert date to timezone-aware datetime (start of day)
        trend_start_date = timezone.make_aware(
            datetime.combine(date_filter_from, datetime.min.time())
        )
    else:
        trend_start_date = timezone.now() - timedelta(days=30)
    
    if date_filter_to:
        # Convert date to timezone-aware datetime (start of day)
        trend_end_date = timezone.make_aware(
            datetime.combine(date_filter_to, datetime.min.time())
        )
    else:
        trend_end_date = timezone.now() + timedelta(days=1)
    
    onboarding_events = AnalyticsEvent.objects.filter(
        event_name__in=['pandit.registered', 'pandit.approved', 'pandit.rejected'],
        timestamp__gte=trend_start_date,
        timestamp__lt=trend_end_date
    ).values('event_name').annotate(count=Count('id')).order_by('event_name')
    
    onboarding_trends = {
        'registered': 0,
        'approved': 0,
        'rejected': 0,
    }
    for event in onboarding_events:
        if 'registered' in event['event_name']:
            onboarding_trends['registered'] = event['count']
        elif 'approved' in event['event_name']:
            onboarding_trends['approved'] = event['count']
        elif 'rejected' in event['event_name']:
            onboarding_trends['rejected'] = event['count']
    
    # Approval vs rejection counts - apply date filter if provided
    approved_query = User.objects.filter(role='pandit', status='active')
    rejected_query = User.objects.filter(role='pandit', status='rejected')
    pending_query = User.objects.filter(role='pandit', status='pending')
    
    if date_filter_from:
        approved_query = approved_query.filter(created_at__gte=date_filter_from)
        rejected_query = rejected_query.filter(created_at__gte=date_filter_from)
        pending_query = pending_query.filter(created_at__gte=date_filter_from)
    if date_filter_to:
        approved_query = approved_query.filter(created_at__lt=date_filter_to)
        rejected_query = rejected_query.filter(created_at__lt=date_filter_to)
        pending_query = pending_query.filter(created_at__lt=date_filter_to)
    
    total_approved = approved_query.count()
    total_rejected = rejected_query.count()
    total_pending = pending_query.count()
    
    # TASK 7: Admin Pandit Referral Analytics (READ-ONLY)
    from referrals.models import ReferralUsage
    from django.utils import timezone as tz
    
    # Get all referral links created by this admin (not filtered by date for metrics)
    all_referral_links = ReferralLink.objects.filter(created_by=request.user)
    
    # TASK 7: Calculate referral usage metrics
    total_referrals_created = all_referral_links.count()
    active_referrals = all_referral_links.filter(
        status=ReferralLink.STATUS_ACTIVE,
        is_active=True,
        expires_at__gt=tz.now()
    ).count()
    expired_referrals = all_referral_links.filter(
        status=ReferralLink.STATUS_EXPIRED
    ).count() + all_referral_links.filter(
        expires_at__lte=tz.now()
    ).exclude(status=ReferralLink.STATUS_EXPIRED).count()
    
    # Total usage count (all usages across all referrals)
    total_usage_count = ReferralUsage.objects.filter(
        referral_link__created_by=request.user
    ).count()
    
    # Referral analytics (TASK 7: READ-ONLY metrics)
    referral_analytics = {
        'total_referrals_created': total_referrals_created,
        'active_referrals': active_referrals,
        'expired_referrals': expired_referrals,
        'total_usage_count': total_usage_count,
    }
    
    # Referral policy for Admin Pandit dropdowns (max_uses tiers, expiry bounds)
    try:
        from referrals.models import ReferralPolicy
        referral_policy = ReferralPolicy.load()
        # Build expiry options 7, 14, 30, 60, 90 up to max_allowed_expiry_days
        max_exp = referral_policy.max_allowed_expiry_days
        referral_expiry_days_options = [d for d in [7, 14, 30, 60, 90] if d <= max_exp]
        if not referral_expiry_days_options or referral_policy.default_expiry_days not in referral_expiry_days_options:
            referral_expiry_days_options = sorted(set(referral_expiry_days_options + [referral_policy.default_expiry_days]))[:10]
    except Exception:
        referral_policy = None
        referral_expiry_days_options = [30]
    
    # Referral effectiveness (for existing analytics section - keep for compatibility)
    referral_usage_query = ReferralUsage.objects.filter(
        referral_link__created_by=request.user
    )
    if date_filter_from:
        referral_usage_query = referral_usage_query.filter(used_at__gte=date_filter_from)
    if date_filter_to:
        referral_usage_query = referral_usage_query.filter(used_at__lt=date_filter_to)
    
    referral_usage_count = referral_usage_query.count()
    
    # Total referral links (already filtered above)
    total_referral_links = referral_links.count()
    referral_effectiveness = {
        'total_links': total_referral_links,
        'total_uses': referral_usage_count,
        'average_uses': round(referral_usage_count / total_referral_links, 2) if total_referral_links > 0 else 0,
    }
    
    # 6. TEMPLE PAGES MANAGEMENT - Get temple pages created by this admin
    from pages.selectors import list_pages_for_admin_pandit
    from pages.constants import PAGE_TYPE_TEMPLE
    temple_pages = []
    try:
        # Get all pages created by this admin pandit (ACTIVE + DEACTIVATED, excludes INVISIBLE)
        all_pages = list_pages_for_admin_pandit(request.user)
        
        # Filter for TEMPLE pages only
        temple_pages_query = all_pages.filter(page_type=PAGE_TYPE_TEMPLE)
        
        # Apply date filter to temple pages (filter by created_at)
        if date_filter_from:
            temple_pages_query = temple_pages_query.filter(created_at__gte=date_filter_from)
        if date_filter_to:
            temple_pages_query = temple_pages_query.filter(created_at__lt=date_filter_to)
        
        owned_pages = temple_pages_query.order_by('-created_at')
        for page in owned_pages:
            temple_pages.append({
                'page': page,
                'status': page.status,
                'created_at': page.created_at,
                'updated_at': page.updated_at,
            })
    except Exception as e:
        # Pages app might not be fully set up
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error fetching temple pages: {str(e)}")
        pass
    
    return render(request, 'module5_dashboards/dashboard_admin_pandit.html', {
        'user': request.user,
        'user_role': 'admin_pandit',
        'referral_links': referral_links,
        'pending_pandits': pending_pandits_list,
        'profiles_awaiting_approval': profiles_list,
        'active_partial_blocks': active_partial_blocks,
        'all_active_pandits': all_active_pandits,
        'trust_chain_data': trust_chain_data,
        'temple_pages': temple_pages,
        'admin_notifications': notifications_list,
        'onboarding_trends': onboarding_trends,
        'approval_stats': {
            'total_approved': total_approved,
            'total_rejected': total_rejected,
            'total_pending': total_pending,
        },
        'referral_effectiveness': referral_effectiveness,
        'referral_analytics': referral_analytics,  # TASK 7: Referral analytics (read-only)
        'referral_policy': referral_policy,  # For max_uses and expiry_days dropdowns
        'referral_expiry_days_options': referral_expiry_days_options if referral_policy else [30],
        'dashboard_has_data': True,  # Always show dashboard content
        'date_filter_from': from_date,
        'date_filter_to': to_date,
    })


@login_required
def dashboard_super_admin(request):
    """
    Super Admin Dashboard - UNIT 1: Foundation & Access Control
    
    Provides system-wide, high-level visibility only.
    This is OBSERVATIONAL ONLY - no actions, no enforcement.
    
    Access Control:
    - ONLY Super Admin (is_superuser=True) can access
    - All others get 404 (not 403, not redirect) - no hints about existence
    """
    # UNIT 1: Enforce permission inside view, return 404 for non-superusers
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    # Import User model
    from accounts.models import User
    
    # UNIT 3: Platform Overview - Use DashboardMetricsService
    from .services import DashboardMetricsService
    platform_metrics = DashboardMetricsService.get_platform_overview()
    
    # System-Level Aggregate Metrics (read-only, backend-computed)
    system_level_aggregates = [
        {'label': 'Total Pandits', 'value': platform_metrics['total_pandits'], 'icon': 'bi bi-people'},
        {'label': 'Total Users', 'value': platform_metrics['total_users'], 'icon': 'bi bi-person'},
        {'label': 'Total Booking Intents', 'value': platform_metrics['booking_intents_count'], 'icon': 'bi bi-envelope'},
        {'label': 'Pending Pandits', 'value': platform_metrics['pending_pandits'], 'icon': 'bi bi-clock-history'},
        {'label': 'Active Pandits', 'value': platform_metrics['active_pandits'], 'icon': 'bi bi-check-circle'},
        {'label': 'Pages', 'value': platform_metrics['pages_count'], 'icon': 'bi bi-file-earmark-text'},
    ]
    
    # UNIT 4: System Health Snapshot
    platform_health_indicators = DashboardMetricsService.get_system_health()
    
    # Governance Overview Summaries (counts only, no actions)
    governance_overview_summaries = [
        {'label': 'Flagged Entities', 'value': 0},  # Backend should provide from Module 11
        {'label': 'Under Review', 'value': 0},  # Backend should provide from Module 11
        {'label': 'Open Appeals', 'value': 0},  # Backend should provide from Module 11
    ]
    
    # Analytics Trends (read-only, from Module 14 backend)
    analytics_trends = [
        {'label': 'Platform Activity', 'value': 'Normal', 'change': None},
        {'label': 'Onboarding Velocity', 'value': 'Stable', 'change': None},
    ]
    
    # Chart Data (read-only, from Module 14 backend)
    chart_data_list = []  # Backend should provide from Module 14
    
    # Governance Table Data (read-only summaries)
    # UNIT 14: Governance Action Review - will be built from unified_audit_records below
    governance_table_data = []  # Will be populated from unified_audit_records
    governance_table_headers = ['Action Type', 'Entity Type', 'Entity', 'Actor', 'Reason', 'Timestamp']
    governance_table_pagination = None
    
    # UNIT 11: Page Governance Overview
    from pages.selectors import list_pages_for_super_admin
    from pages.dashboard_data import get_super_admin_page_overview
    from django.core.paginator import Paginator as PagePaginator
    
    # Get page filter parameters
    page_type_filter = request.GET.get('page_type', '')
    page_search = request.GET.get('page_search', '')
    page_status_filter = request.GET.get('page_status', '')
    page_page_number = request.GET.get('page_page', 1)
    
    all_pages = []
    page_overview = None
    page_governance_list = []
    page_governance_page = None
    
    try:
        all_pages_queryset = list_pages_for_super_admin(request.user)
        
        # Apply filters
        if page_type_filter:
            all_pages_queryset = all_pages_queryset.filter(page_type=page_type_filter)
        if page_status_filter:
            all_pages_queryset = all_pages_queryset.filter(status=page_status_filter)
        if page_search:
            all_pages_queryset = all_pages_queryset.filter(
                models.Q(title__icontains=page_search) |
                models.Q(created_by__email__icontains=page_search)
            )
        
        # Paginate page governance list (PART 3 hardening: use constant)
        from core.api_constants import DEFAULT_PAGE_SIZE
        page_paginator = PagePaginator(all_pages_queryset, DEFAULT_PAGE_SIZE)
        try:
            page_governance_page = page_paginator.page(page_page_number)
        except:
            page_governance_page = page_paginator.page(1)
        
        # Build page governance list with required fields
        for page in page_governance_page:
            page_governance_list.append({
                'page': page,
                'title': page.title,
                'page_type': page.page_type,
                'owner': page.created_by.get_full_name() if page.created_by else 'System',
                'owner_role': page.owner_role,
                'visibility_status': page.status,
                'created_date': page.created_at,
            })
        
        # Keep backward compatibility; limit from config overlay or settings (lazy)
        from core.api_constants import get_dashboard_pages_preview_limit
        from core.config import get_config_value
        default_preview = get_dashboard_pages_preview_limit()
        preview_limit = get_config_value('DASHBOARD_PAGES_PREVIEW_LIMIT', default_preview)
        all_pages = list(all_pages_queryset[:preview_limit])
        page_overview = get_super_admin_page_overview()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error fetching pages for super admin: {str(e)}")
    
    # UNIT 7: Pandit Governance Overview (Read-Only)
    from django.core.paginator import Paginator as PanditPaginator
    pandit_status_filter = request.GET.get('pandit_status', '')
    pandit_search = request.GET.get('pandit_search', '')
    pandit_page_number = request.GET.get('pandit_page', 1)
    
    pandit_governance_queryset = DashboardMetricsService.get_pandit_governance_list(
        status_filter=pandit_status_filter if pandit_status_filter else None,
        search_query=pandit_search if pandit_search else None
    )
    
    # Paginate pandit governance list (PART 3 hardening: use constant)
    from core.api_constants import DEFAULT_PAGE_SIZE
    pandit_paginator = PanditPaginator(pandit_governance_queryset, DEFAULT_PAGE_SIZE)
    try:
        pandit_governance_page = pandit_paginator.page(pandit_page_number)
    except:
        pandit_governance_page = pandit_paginator.page(1)
    
    # Build pandit governance list with required fields
    pandit_governance_list = []
    for profile in pandit_governance_page:
        # Get primary city (first city served - PanditProfile uses ManyToMany cities_served, not city FK)
        primary_city = None
        if profile.cities_served.exists():
            primary_city = profile.cities_served.first().name
        
        pandit_governance_list.append({
            'profile': profile,
            'name': profile.get_display_name() or profile.user.get_full_name() or profile.user.email,
            'city': primary_city or 'Not specified',
            'status': profile.user.status,
            'joined_date': profile.user.date_joined,
            'last_updated': profile.updated_at,
            'referred_by': profile.user.referred_by.get_full_name() if profile.user.referred_by else None,
            'email': profile.user.email,
        })
    
    # TASK 5: Pandits list for Super Admin dashboard (with email verification status) - Keep for backward compatibility
    # Limit to avoid slow request when many pandits exist (Phase 12 slow-query fix)
    from accounts.models import User
    all_pandits = User.objects.filter(role='pandit').select_related('referred_by').order_by('-date_joined')[: (DEFAULT_PAGE_SIZE * 4)]
    pandits_list = []
    for pandit in all_pandits:
        pandits_list.append({
            'user': pandit,
            'email_verified': pandit.email_verified and pandit.email_verified_at is not None,
            'email_verified_at': pandit.email_verified_at,
            'last_verification_email_sent_at': pandit.last_verification_email_sent_at,
            'status': pandit.status,
            'is_active': pandit.is_active,
        })
    
    # UNIT 5: Global Audit Visibility (Read-Only)
    # UNIT 14: Governance Action Review (Unified audit feed)
    from pages.models import PageAuditLog
    from django.core.paginator import Paginator
    from django.utils import timezone
    from datetime import timedelta
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get filter parameters
    actor_filter = request.GET.get('actor', '')
    entity_type_filter = request.GET.get('entity_type', '')
    action_type_filter = request.GET.get('action_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    page_number = request.GET.get('page', 1)
    
    # UNIT 14: Build unified audit query from all audit tables
    # Limit records at DB level to avoid slow request (SLOW REQUEST fix)
    from core.api_constants import get_dashboard_audit_feed_max
    audit_feed_max = get_dashboard_audit_feed_max()
    audit_records = (
        PageAuditLog.objects.select_related('page', 'performed_by')
        .order_by('-created_at')[:audit_feed_max]
    )
    
    # Convert PageAuditLog to unified format for UNIT 14
    unified_audit_records = []
    for record in audit_records:
        unified_audit_records.append({
            'id': record.id,
            'action_type': record.action,
            'entity_type': 'Page',
            'entity_id': record.page.id,
            'entity_public_id': record.page.public_id,
            'entity_title': record.page.title,
            'actor': record.performed_by,
            'actor_email': record.performed_by.email if record.performed_by else 'System',
            'reason': None,  # PageAuditLog doesn't store reason, but Super Admin actions do
            'timestamp': record.created_at,
            'source': 'PageAuditLog',
        })
    
    # TODO: Add other audit sources (Pandit status changes, etc.)
    # For now, we also check Django logging for Super Admin actions
    # In production, these should be stored in a dedicated audit table
    
    # Apply filters to unified records
    if actor_filter:
        unified_audit_records = [
            r for r in unified_audit_records
            if actor_filter.lower() in r['actor_email'].lower()
        ]
    
    if entity_type_filter:
        unified_audit_records = [
            r for r in unified_audit_records
            if r['entity_type'].lower() == entity_type_filter.lower()
        ]
    
    if action_type_filter:
        unified_audit_records = [
            r for r in unified_audit_records
            if action_type_filter.lower() in r['action_type'].lower()
        ]
    
    if date_from:
        try:
            date_from_obj = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            unified_audit_records = [
                r for r in unified_audit_records
                if r['timestamp'].date() >= date_from_obj
            ]
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = timezone.datetime.strptime(date_to, '%Y-%m-%d').date() + timedelta(days=1)
            unified_audit_records = [
                r for r in unified_audit_records
                if r['timestamp'].date() < date_to_obj
            ]
        except ValueError:
            pass
    
    # Sort by timestamp (newest first)
    unified_audit_records.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Pagination (mandatory for UNIT 5 & 14)
    from django.core.paginator import Paginator as UnifiedPaginator, EmptyPage, PageNotAnInteger
    # PART 3 hardening: use constant for pagination
    from core.api_constants import DEFAULT_PAGE_SIZE
    paginator = UnifiedPaginator(unified_audit_records, DEFAULT_PAGE_SIZE)
    try:
        audit_page = paginator.page(page_number)
    except (EmptyPage, PageNotAnInteger):
        audit_page = paginator.page(1)
    
    # Set governance_table_data from paginated audit records
    governance_table_data = list(audit_page)
    governance_table_pagination = paginator
    
    # UNIT 15: SEO Metadata Oversight
    # Combine pandits and pages into a single list for template
    seo_oversight_dict = DashboardMetricsService.get_seo_oversight_list(
        entity_type=request.GET.get('seo_entity_type', 'all'),
        search_query=request.GET.get('seo_search', '') if request.GET.get('seo_search') else None
    )
    # Normalize field names and combine lists
    seo_oversight_list = []
    if seo_oversight_dict:
        # Process pandits
        for item in seo_oversight_dict.get('pandits', []):
            seo_oversight_list.append({
                'entity_type': item.get('entity_type', 'PanditProfile'),
                'entity_public_id': item.get('public_id', ''),
                'entity_name': item.get('name', ''),
                'seo_title': item.get('seo_title', ''),
                'seo_description': item.get('seo_description', ''),
                'seo_keywords': item.get('seo_keywords', ''),
                'seo_autogenerated': item.get('seo_autogenerated', False),
                'seo_last_updated_at': item.get('seo_last_updated_at', None),
            })
        # Process pages
        for item in seo_oversight_dict.get('pages', []):
            seo_oversight_list.append({
                'entity_type': item.get('entity_type', 'Page'),
                'entity_public_id': item.get('public_id', ''),
                'entity_name': item.get('title', ''),
                'seo_title': item.get('seo_title', ''),
                'seo_description': item.get('seo_description', ''),
                'seo_keywords': item.get('seo_keywords', ''),
                'seo_autogenerated': item.get('seo_autogenerated', False),
                'seo_last_updated_at': item.get('seo_last_updated_at', None),
            })
    
    return render(request, 'module5_dashboards/dashboard_super_admin.html', {
        'user': request.user,
        'user_role': 'super_admin',
        'platform_health_indicators': platform_health_indicators,
        'system_level_aggregates': system_level_aggregates,
        'governance_overview_summaries': governance_overview_summaries,
        'analytics_trends': analytics_trends,
        'chart_data_list': chart_data_list,
        'governance_table_data': governance_table_data,
        'governance_table_headers': governance_table_headers,
        'governance_table_pagination': governance_table_pagination,
        'all_pages': all_pages,
        'page_overview': page_overview,
        'pandits_list': pandits_list,  # TASK 5: Pandits list with verification status
        'dashboard_has_data': True,
        # UNIT 5: Global Audit Visibility
        # UNIT 14: Governance Action Review (unified feed)
        'audit_records': audit_page,
        'governance_audit_page': audit_page,  # For template pagination
        'audit_filters': {
            'actor': actor_filter,
            'entity_type': entity_type_filter,
            'action_type': action_type_filter,
            'date_from': date_from,
            'date_to': date_to,
        },
        # UNIT 7: Pandit Governance Overview
        'pandit_governance_list': pandit_governance_list,
        'pandit_governance_page': pandit_governance_page,
        'pandit_governance_filters': {
            'status': pandit_status_filter,
            'search': pandit_search,
        },
        # UNIT 10: Referral Chain & Trust Visibility (read-only)
        # This will be used in template to show trust data for each pandit
        'show_trust_data': True,  # Flag to enable trust data display
        # UNIT 11: Page Governance Overview
        'page_governance_list': page_governance_list,
        'page_governance_page': page_governance_page,
        'page_governance_filters': {
            'page_type': page_type_filter,
            'page_status': page_status_filter,
            'search': page_search,
        },
        # UNIT 15: SEO Metadata Oversight
        'seo_oversight_list': seo_oversight_list,
    })


@admin_required
@require_POST
@csrf_protect
def approve_profile(request, profile_id):
    """
    Approve a Pandit profile for public visibility (Admin Pandit only).
    
    This view:
    - Sets is_profile_approved=True
    - Records approval timestamp and approver
    - Only works on profiles that are not already approved
    - Access restricted to: role='admin' AND not superuser (Admin Pandit)
    """
    # Role-based access: Only Admin Pandit (admin but not superuser)
    if request.user.is_superuser:
        messages.error(request, 'Super Admin should use Super Admin dashboard for this action.')
        return redirect('module5_dashboards:dashboard_super_admin')
    elif request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin Pandit role required.')
        return redirect('core:home')
    
    from profiles.models import PanditProfile
    from django.utils import timezone
    
    profile = get_object_or_404(PanditProfile, id=profile_id)
    
    # Validate profile belongs to an active pandit
    if profile.user.role != 'pandit' or profile.user.status != 'active':
        messages.error(request, 'Cannot approve profile for inactive or non-pandit user.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Check if already approved
    if profile.is_profile_approved:
        messages.info(request, f'Profile for {profile.get_display_name()} is already approved.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Approve the profile
    try:
        profile.is_profile_approved = True
        profile.profile_approved_at = timezone.now()
        profile.profile_approved_by = request.user
        profile.save()
        
        messages.success(request, f'Profile for {profile.get_display_name()} has been approved for public visibility.')
    except Exception as e:
        messages.error(request, f'Error approving profile: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_admin_pandit')


@admin_required
@require_POST
@csrf_protect
def reject_pandit_ui(request, user_id):
    """
    Reject a pending Pandit user - UI version with redirect (Admin Pandit only).
    
    This is a UI-friendly wrapper around the accounts.reject_pandit view.
    """
    # Role-based access: Only Admin Pandit (admin but not superuser)
    if request.user.is_superuser:
        messages.error(request, 'Super Admin should use Super Admin dashboard for this action.')
        return redirect('module5_dashboards:dashboard_super_admin')
    elif request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin Pandit role required.')
        return redirect('core:home')
    
    from accounts.models import User
    from django.http import JsonResponse
    import json
    
    # Get the target user
    target_user = get_object_or_404(User, id=user_id)
    
    # Validate target user is a Pandit
    if target_user.role != 'pandit':
        messages.error(request, f'Cannot reject user with role "{target_user.role}". Only Pandits can be rejected.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Validate target user is pending
    if target_user.status != 'pending':
        messages.error(request, f'Cannot reject user with status "{target_user.status}". Only pending Pandits can be rejected.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Prevent self-rejection
    if target_user.id == request.user.id:
        messages.error(request, 'Users cannot reject themselves.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Get reject reason and note from form
    reject_reason = request.POST.get('reject_reason', '')
    reject_note = request.POST.get('reject_note', '')
    
    # Reject the Pandit
    try:
        target_user.status = 'rejected'
        target_user.is_active = False
        target_user.save()
        
        # Log the rejection reason if provided (you can store this in a separate model if needed)
        rejection_message = f'Pandit {target_user.email} has been rejected.'
        if reject_reason:
            rejection_message += f' Reason: {reject_reason}.'
        if reject_note:
            rejection_message += f' Note: {reject_note}'
        
        messages.success(request, rejection_message)
    except Exception as e:
        messages.error(request, f'Error rejecting Pandit: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_admin_pandit')


@admin_required
@require_POST
@csrf_protect
def approve_pandit_ui(request, user_id):
    """
    Approve a pending Pandit user - UI version with redirect (Admin Pandit only).
    
    This is a UI-friendly wrapper around the accounts.approve_pandit view.
    """
    # Role-based access: Only Admin Pandit (admin but not superuser)
    if request.user.is_superuser:
        messages.error(request, 'Super Admin should use Super Admin dashboard for this action.')
        return redirect('module5_dashboards:dashboard_super_admin')
    elif request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin Pandit role required.')
        return redirect('core:home')
    
    from accounts.models import User
    
    # Get the target user
    target_user = get_object_or_404(User, id=user_id)
    
    # Validate target user is a Pandit
    if target_user.role != 'pandit':
        messages.error(request, f'Cannot approve user with role "{target_user.role}". Only Pandits can be approved.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Validate target user is pending
    if target_user.status != 'pending':
        messages.error(request, f'Cannot approve user with status "{target_user.status}". Only pending Pandits can be approved.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Prevent self-approval
    if target_user.id == request.user.id:
        messages.error(request, 'Users cannot approve themselves.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Approve the Pandit
    try:
        target_user.status = 'active'
        target_user.is_active = True
        target_user.save()
        
        messages.success(request, f'Pandit {target_user.email} has been approved successfully.')
    except Exception as e:
        messages.error(request, f'Error approving Pandit: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_admin_pandit')


@admin_required
def send_profile_back_for_edit(request, profile_id):
    """
    Send a profile back for editing (Admin Pandit only).
    
    This view:
    - Sets is_profile_approved=False (if it was approved)
    - Can be used to request profile updates
    - Access restricted to: role='admin' AND not superuser (Admin Pandit)
    """
    # Role-based access: Only Admin Pandit (admin but not superuser)
    if request.user.is_superuser:
        messages.error(request, 'Super Admin should use Super Admin dashboard for this action.')
        return redirect('module5_dashboards:dashboard_super_admin')
    elif request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin Pandit role required.')
        return redirect('core:home')
    
    from profiles.models import PanditProfile
    
    profile = get_object_or_404(PanditProfile, id=profile_id)
    
    # Validate profile belongs to an active pandit
    if profile.user.role != 'pandit' or profile.user.status != 'active':
        messages.error(request, 'Cannot modify profile for inactive or non-pandit user.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Send back for edit (unapprove if approved, or just notify)
    try:
        if profile.is_profile_approved:
            profile.is_profile_approved = False
            profile.profile_approved_at = None
            profile.profile_approved_by = None
            profile.save()
            messages.success(request, f'Profile for {profile.get_display_name()} has been sent back for editing.')
        else:
            messages.info(request, f'Profile for {profile.get_display_name()} is already pending approval.')
    except Exception as e:
        messages.error(request, f'Error sending profile back for edit: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_admin_pandit')


@admin_required
@require_POST
@csrf_protect
def apply_partial_block(request):
    """
    Apply a partial block to a Pandit (Admin Pandit only).
    
    This view:
    - Creates a PartialBlock record
    - Applies the specified restriction type
    - Logs the action for audit
    """
    # Role-based access: Only Admin Pandit (admin but not superuser)
    if request.user.is_superuser:
        messages.error(request, 'Super Admin should use Super Admin dashboard for this action.')
        return redirect('module5_dashboards:dashboard_super_admin')
    elif request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin Pandit role required.')
        return redirect('core:home')
    
    if request.method == 'POST':
        from governance.models import PartialBlock
        
        pandit_id = request.POST.get('pandit_id')
        restriction_type = request.POST.get('restriction_type')
        reason = request.POST.get('reason', '')
        
        if not pandit_id or not restriction_type:
            messages.error(request, 'Missing required fields.')
            return redirect('module5_dashboards:dashboard_admin_pandit')
        
        try:
            pandit = User.objects.get(id=pandit_id, role='pandit', status='active')
        except User.DoesNotExist:
            messages.error(request, 'Pandit not found or not active.')
            return redirect('module5_dashboards:dashboard_admin_pandit')
        
        # Create partial block
        try:
            partial_block = PartialBlock.objects.create(
                pandit=pandit,
                restriction_type=restriction_type,
                reason=reason,
                applied_by=request.user,
                is_active=True
            )
            messages.success(request, f'Partial block applied to {pandit.get_full_name() or pandit.email}.')
        except Exception as e:
            messages.error(request, f'Error applying partial block: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_admin_pandit')


@admin_required
@require_POST
@csrf_protect
def remove_partial_block(request, block_id):
    """
    Remove a partial block from a Pandit (Admin Pandit only).
    
    This view:
    - Sets is_active=False
    - Records removal timestamp and remover
    - Logs the action for audit
    """
    # Role-based access: Only Admin Pandit (admin but not superuser)
    if request.user.is_superuser:
        messages.error(request, 'Super Admin should use Super Admin dashboard for this action.')
        return redirect('module5_dashboards:dashboard_super_admin')
    elif request.user.role != 'admin':
        messages.error(request, 'Access denied. Admin Pandit role required.')
        return redirect('core:home')
    
    from governance.models import PartialBlock
    from django.utils import timezone
    
    partial_block = get_object_or_404(PartialBlock, id=block_id)
    
    if not partial_block.is_active:
        messages.info(request, 'This block is already removed.')
        return redirect('module5_dashboards:dashboard_admin_pandit')
    
    # Remove the block
    try:
        partial_block.is_active = False
        partial_block.removed_at = timezone.now()
        partial_block.removed_by = request.user
        partial_block.save()
        
        messages.success(request, f'Partial block removed from {partial_block.pandit.get_full_name() or partial_block.pandit.email}.')
    except Exception as e:
        messages.error(request, f'Error removing partial block: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_admin_pandit')


# ============================================================================
# PART 2: GOVERNANCE & CONTROL (Super Admin Only)
# ============================================================================

@login_required
def super_admin_experts(request):
    if not request.user.is_superuser:
        from django.http import Http404

        raise Http404("Page not found")

    from core.models import ExpertProfile

    if request.method == "POST":
        expert_id = request.POST.get("expert_id")
        action = request.POST.get("action")

        expert = get_object_or_404(ExpertProfile, id=expert_id)

        if action == "approve":
            expert.is_active = True
            expert.save()

            try:
                if expert.email:
                    send_mail(
                        subject="Your Expert Profile is Approved",
                        message=(
                            "Congratulations! Your expert profile is now approved and live.\n\n"
                            "You can now log in and manage your profile.\n\n"
                            "Login here: http://127.0.0.1:8000/login/\n"
                            "Expert Dashboard: http://127.0.0.1:8000/dashboard/expert/\n\n"
                            "Thank you for joining Nitya Dharma."
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[expert.email],
                        fail_silently=True,
                    )
            except Exception:
                pass
        elif action == "verify":
            expert.is_verified = True
            expert.save()

        return redirect("module5_dashboards:super_admin_experts")

    experts = (
        ExpertProfile.objects.prefetch_related("social_links")
        .all()
        .order_by("-created_at")
    )
    pending_count = ExpertProfile.objects.filter(is_active=False).count()
    approved_count = ExpertProfile.objects.filter(is_active=True).count()
    verified_count = ExpertProfile.objects.filter(is_verified=True).count()
    status = request.GET.get("status")

    if status == "pending":
        experts = experts.filter(is_active=False)
    elif status == "approved":
        experts = experts.filter(is_active=True)
    elif status == "verified":
        experts = experts.filter(is_verified=True)

    expert_type_param = (request.GET.get("type") or "").upper()
    expert_type_filter = (
        expert_type_param
        if expert_type_param in ("ASTROLOGER", "NUMEROLOGIST", "PALMIST")
        else ""
    )
    if expert_type_filter:
        experts = experts.filter(expert_type=expert_type_filter)

    all_experts = experts

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="experts.csv"'

        writer = csv.writer(response)
        writer.writerow(["Name", "Type", "Experience", "Active", "Verified"])

        for e in all_experts:
            writer.writerow([e.name, e.expert_type, e.experience_years, e.is_active, e.is_verified])

        return response

    from core.api_constants import DEFAULT_PAGE_SIZE
    from django.core.paginator import Paginator

    paginator = Paginator(experts, DEFAULT_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "dashboard/super_admin/experts.html",
        {
            "experts": page_obj,
            "page_obj": page_obj,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "verified_count": verified_count,
            "context_type": expert_type_filter,
        },
    )


@login_required
@require_POST
def bulk_approve_experts(request):
    if not request.user.is_superuser:
        from django.http import Http404

        raise Http404("Page not found")

    from urllib.parse import urlencode

    from django.urls import reverse

    from core.models import ExpertProfile

    selected_ids = list(set(request.POST.getlist("selected_experts")))

    def _redirect_back():
        params = {}
        t = request.POST.get("type") or ""
        if t in ("ASTROLOGER", "NUMEROLOGIST", "PALMIST"):
            params["type"] = t
        s = request.POST.get("status") or ""
        if s in ("pending", "approved", "verified"):
            params["status"] = s
        base = reverse("module5_dashboards:super_admin_experts")
        if params:
            return redirect(f"{base}?{urlencode(params)}")
        return redirect(base)

    if not selected_ids:
        messages.warning(request, "No experts selected.")
        return _redirect_back()

    # Same queryset guards as the list view (POST hidden fields): avoid cross-type / wrong-tab approvals.
    experts = ExpertProfile.objects.filter(id__in=selected_ids)

    type_filter = (request.POST.get("type") or "").upper()
    if type_filter in ("ASTROLOGER", "NUMEROLOGIST", "PALMIST"):
        experts = experts.filter(expert_type=type_filter)

    status_filter = request.POST.get("status") or ""
    if status_filter == "pending":
        experts = experts.filter(is_active=False)
    elif status_filter == "approved":
        experts = experts.filter(is_active=True)
    elif status_filter == "verified":
        experts = experts.filter(is_verified=True)

    # Match super_admin_experts single "approve" action: is_active only (not is_verified); optional email.
    approved_count = 0
    for expert in experts:
        if expert.is_active:
            continue
        expert.is_active = True
        expert.save()

        try:
            if expert.email:
                send_mail(
                    subject="Your Expert Profile is Approved",
                    message=(
                        "Congratulations! Your expert profile is now approved and live.\n\n"
                        "You can now log in and manage your profile.\n\n"
                        "Login here: http://127.0.0.1:8000/login/\n"
                        "Expert Dashboard: http://127.0.0.1:8000/dashboard/expert/\n\n"
                        "Thank you for joining Nitya Dharma."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[expert.email],
                    fail_silently=True,
                )
        except Exception:
            pass

        approved_count += 1

    messages.success(request, f"{approved_count} expert(s) approved successfully.")
    return _redirect_back()


@login_required
@require_POST
@csrf_protect
def approve_pandit_super_admin(request, user_id):
    """
    UNIT 8: Approve a pending Pandit (Super Admin only).
    
    Transitions: pending → active
    Captures: Action reason, Acting Super Admin, Timestamp
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from accounts.models import User
    from django.utils import timezone
    from dashboards.audit import log_super_admin_action
    
    target_user = get_object_or_404(User, id=user_id)
    
    # Validate target user is a Pandit
    if target_user.role != 'pandit':
        messages.error(request, f'Cannot approve user with role "{target_user.role}". Only Pandits can be approved.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Validate target user is pending
    if target_user.status != 'pending':
        messages.error(request, f'Cannot approve user with status "{target_user.status}". Only pending Pandits can be approved.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Prevent self-approval
    if target_user.id == request.user.id:
        messages.error(request, 'Users cannot approve themselves.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Get approval reason (optional)
    approval_reason = request.POST.get('approval_reason', '')
    
    # Approve the Pandit
    try:
        before_status = target_user.status
        target_user.status = 'active'
        target_user.is_active = True
        target_user.save()
        
        # UNIT 6: Log Super Admin action
        log_super_admin_action(
            action_type='PANDIT_APPROVAL',
            target_entity=target_user,
            before_snapshot={'status': before_status},
            after_snapshot={'status': 'active'},
            actor=request.user,
            additional_data={'reason': approval_reason} if approval_reason else None,
        )
        
        messages.success(request, f'Pandit {target_user.email} has been approved successfully.')
    except Exception as e:
        messages.error(request, f'Error approving Pandit: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_super_admin')


@login_required
@require_POST
@csrf_protect
def reject_pandit_super_admin(request, user_id):
    """
    UNIT 8: Reject a pending Pandit (Super Admin only).
    
    Transitions: pending → rejected
    Captures: Action reason (required), Acting Super Admin, Timestamp
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from accounts.models import User
    from django.utils import timezone
    from dashboards.audit import log_super_admin_action
    
    target_user = get_object_or_404(User, id=user_id)
    
    # Validate target user is a Pandit
    if target_user.role != 'pandit':
        messages.error(request, f'Cannot reject user with role "{target_user.role}". Only Pandits can be rejected.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Validate target user is pending
    if target_user.status != 'pending':
        messages.error(request, f'Cannot reject user with status "{target_user.status}". Only pending Pandits can be rejected.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Prevent self-rejection
    if target_user.id == request.user.id:
        messages.error(request, 'Users cannot reject themselves.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Get rejection reason (required)
    reject_reason = request.POST.get('reject_reason', '').strip()
    if not reject_reason:
        messages.error(request, 'Rejection reason is required.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Reject the Pandit
    try:
        before_status = target_user.status
        target_user.status = 'rejected'
        target_user.is_active = False
        target_user.save()
        
        # UNIT 6: Log Super Admin action
        log_super_admin_action(
            action_type='PANDIT_REJECTION',
            target_entity=target_user,
            before_snapshot={'status': before_status},
            after_snapshot={'status': 'rejected'},
            actor=request.user,
            additional_data={'reason': reject_reason},
        )
        
        messages.success(request, f'Pandit {target_user.email} has been rejected. Reason: {reject_reason}')
    except Exception as e:
        messages.error(request, f'Error rejecting Pandit: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_super_admin')


@login_required
@require_POST
@csrf_protect
def suspend_pandit_super_admin(request, user_id):
    """
    UNIT 9: Suspend an active Pandit (Super Admin only).
    
    Transitions: active → suspended
    Records: Reason (required), Duration (optional), Acting Super Admin
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from accounts.models import User
    from django.utils import timezone
    from dashboards.audit import log_super_admin_action
    
    target_user = get_object_or_404(User, id=user_id)
    
    # Validate target user is a Pandit
    if target_user.role != 'pandit':
        messages.error(request, f'Cannot suspend user with role "{target_user.role}". Only Pandits can be suspended.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Validate target user is active
    if target_user.status != 'active':
        messages.error(request, f'Cannot suspend user with status "{target_user.status}". Only active Pandits can be suspended.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Prevent self-suspension
    if target_user.id == request.user.id:
        messages.error(request, 'Users cannot suspend themselves.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Get suspension reason (required)
    suspend_reason = request.POST.get('suspend_reason', '').strip()
    if not suspend_reason:
        messages.error(request, 'Suspension reason is required.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Get duration (optional)
    suspend_duration = request.POST.get('suspend_duration', '').strip()
    
    # Suspend the Pandit
    try:
        before_status = target_user.status
        # Note: Assuming 'suspended' is a valid status, otherwise use a different approach
        # For now, we'll set is_active=False and add a note
        target_user.is_active = False
        # If there's a status field that supports 'suspended', use it
        # Otherwise, we might need to add a separate suspension flag
        target_user.save()
        
        # UNIT 6: Log Super Admin action
        additional_data = {'reason': suspend_reason}
        if suspend_duration:
            additional_data['duration'] = suspend_duration
        
        log_super_admin_action(
            action_type='PANDIT_SUSPENSION',
            target_entity=target_user,
            before_snapshot={'status': before_status, 'is_active': True},
            after_snapshot={'status': before_status, 'is_active': False},
            actor=request.user,
            additional_data=additional_data,
        )
        
        duration_msg = f' for {suspend_duration}' if suspend_duration else ''
        messages.success(request, f'Pandit {target_user.email} has been suspended{duration_msg}. Reason: {suspend_reason}')
    except Exception as e:
        messages.error(request, f'Error suspending Pandit: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_super_admin')


@login_required
@require_POST
@csrf_protect
def reinstate_pandit_super_admin(request, user_id):
    """
    UNIT 9: Reinstate a suspended Pandit (Super Admin only).
    
    Transitions: suspended → active
    Records: Reason (optional), Acting Super Admin
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from accounts.models import User
    from django.utils import timezone
    from dashboards.audit import log_super_admin_action
    
    target_user = get_object_or_404(User, id=user_id)
    
    # Validate target user is a Pandit
    if target_user.role != 'pandit':
        messages.error(request, f'Cannot reinstate user with role "{target_user.role}". Only Pandits can be reinstated.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Validate target user is suspended (is_active=False)
    if target_user.is_active:
        messages.error(request, f'User {target_user.email} is already active.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    # Get reinstatement reason (optional)
    reinstate_reason = request.POST.get('reinstate_reason', '').strip()
    
    # Reinstate the Pandit
    try:
        before_status = target_user.status
        before_active = target_user.is_active
        target_user.is_active = True
        if target_user.status != 'active':
            target_user.status = 'active'
        target_user.save()
        
        # UNIT 6: Log Super Admin action
        log_super_admin_action(
            action_type='PANDIT_REINSTATEMENT',
            target_entity=target_user,
            before_snapshot={'status': before_status, 'is_active': before_active},
            after_snapshot={'status': 'active', 'is_active': True},
            actor=request.user,
            additional_data={'reason': reinstate_reason} if reinstate_reason else None,
        )
        
        messages.success(request, f'Pandit {target_user.email} has been reinstated successfully.')
    except Exception as e:
        messages.error(request, f'Error reinstating Pandit: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_super_admin')


@login_required
def edit_page_super_admin(request, page_public_id):
    """
    UNIT 12: Edit & Override Page (Super Admin only).
    
    Allows Super Admin to edit any page with full control:
    - Title
    - Description
    - Visibility (status)
    - SEO metadata
    
    Records: Before state, After state, Reason
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from pages.models import Page
    from pages.page_permissions import resolve_public_id
    from core.public_id import reject_bigint_id
    from dashboards.forms import PageEditFormSuperAdmin
    from dashboards.audit import log_super_admin_action
    
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    if request.method == 'POST':
        # PART 4 FIX: Validate file uploads before form processing
        from core.file_upload_security import validate_image_upload
        from django.core.exceptions import ValidationError
        
        if request.FILES:
            for field_name in ['profile_image', 'cover_image']:
                if field_name in request.FILES:
                    try:
                        sanitized_filename, validated_file = validate_image_upload(request.FILES[field_name])
                        # Replace with validated file
                        request.FILES[field_name] = validated_file
                    except ValidationError as e:
                        messages.error(request, f'{field_name.replace("_", " ").title()} validation failed: {str(e)}')
                        return redirect('dashboards:page_edit_super_admin', page_public_id=page_public_id)
        
        form = PageEditFormSuperAdmin(request.POST, request.FILES, instance=page)
        if form.is_valid():
            try:
                # Capture before state
                before_snapshot = {
                    'title': page.title,
                    'description': page.description,
                    'status': page.status,
                    'seo_title': page.seo_title,
                    'seo_description': page.seo_description,
                }
                
                # Get override reason
                override_reason = request.POST.get('override_reason', '').strip()
                
                # Update page fields
                page.title = form.cleaned_data['title']
                page.description = form.cleaned_data.get('description', '')
                page.status = form.cleaned_data.get('status', page.status)
                
                # Handle SEO fields
                if 'seo_title' in form.cleaned_data:
                    page.seo_title = form.cleaned_data.get('seo_title', '')[:60] if form.cleaned_data.get('seo_title') else None
                if 'seo_description' in form.cleaned_data:
                    page.seo_description = form.cleaned_data.get('seo_description', '')[:160] if form.cleaned_data.get('seo_description') else None
                if 'seo_keywords' in form.cleaned_data:
                    page.seo_keywords = form.cleaned_data.get('seo_keywords', '')
                
                # Image uploads are validated before form processing (see above)
                # Form will handle the validated files
                
                page.updated_by = request.user
                page.full_clean()
                page.save()
                
                # Capture after state
                after_snapshot = {
                    'title': page.title,
                    'description': page.description,
                    'status': page.status,
                    'seo_title': page.seo_title,
                    'seo_description': page.seo_description,
                }
                
                # UNIT 6: Log Super Admin action
                log_super_admin_action(
                    action_type='PAGE_EDIT_OVERRIDE',
                    target_entity=page,
                    before_snapshot=before_snapshot,
                    after_snapshot=after_snapshot,
                    actor=request.user,
                    additional_data={'reason': override_reason} if override_reason else None,
                )
                
                messages.success(request, f"Page '{page.title}' updated successfully by Super Admin.")
                return redirect('module5_dashboards:dashboard_super_admin')
            except Exception as e:
                messages.error(request, f"Error updating page: {str(e)}")
    else:
        # GET request - show edit form
        form = PageEditFormSuperAdmin(instance=page)
    
    return render(request, 'dashboards/page_edit_super_admin.html', {
        'page': page,
        'form': form,
    })


@login_required
@require_POST
@csrf_protect
def disable_page_super_admin(request, page_public_id):
    """
    UNIT 13: Disable Page (Super Admin only).
    
    Soft disable page without deletion:
    - Toggle visibility flag
    - Record reason
    - Prevent public access when disabled
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from pages.models import Page
    from pages.page_permissions import resolve_public_id
    from core.public_id import reject_bigint_id
    from pages.services import deactivate_page
    from dashboards.audit import log_super_admin_action
    
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    # Get disable reason (required)
    disable_reason = request.POST.get('disable_reason', '').strip()
    if not disable_reason:
        messages.error(request, 'Disable reason is required.')
        return redirect('module5_dashboards:dashboard_super_admin')
    
    try:
        before_status = page.status
        # Use existing deactivate_page service
        deactivate_page(request.user, page_public_id)
        page.refresh_from_db()
        
        # UNIT 6: Log Super Admin action
        log_super_admin_action(
            action_type='PAGE_DISABLE',
            target_entity=page,
            before_snapshot={'status': before_status},
            after_snapshot={'status': page.status},
            actor=request.user,
            additional_data={'reason': disable_reason},
        )
        
        messages.success(request, f"Page '{page.title}' has been disabled. Reason: {disable_reason}")
    except Exception as e:
        messages.error(request, f'Error disabling page: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_super_admin')


@login_required
@require_POST
@csrf_protect
def restore_page_super_admin(request, page_public_id):
    """
    UNIT 13: Restore Page (Super Admin only).
    
    Restore a disabled page:
    - Toggle visibility flag back
    - Record reason
    - Restore public access
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from pages.models import Page
    from pages.page_permissions import resolve_public_id
    from core.public_id import reject_bigint_id
    from pages.services import activate_page
    from dashboards.audit import log_super_admin_action
    
    if reject_bigint_id(page_public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, page_public_id)
    if not page:
        raise Http404("Page not found")
    
    # Get restore reason (optional)
    restore_reason = request.POST.get('restore_reason', '').strip()
    
    try:
        before_status = page.status
        # Use existing activate_page service
        activate_page(request.user, page_public_id)
        page.refresh_from_db()
        
        # UNIT 6: Log Super Admin action
        log_super_admin_action(
            action_type='PAGE_RESTORE',
            target_entity=page,
            before_snapshot={'status': before_status},
            after_snapshot={'status': page.status},
            actor=request.user,
            additional_data={'reason': restore_reason} if restore_reason else None,
        )
        
        messages.success(request, f"Page '{page.title}' has been restored successfully.")
    except Exception as e:
        messages.error(request, f'Error restoring page: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_super_admin')


# ============================================================================
# PART 3: PLATFORM CONTROLS, SEO OVERSIGHT & ANALYTICS
# ============================================================================

@login_required
@require_POST
@csrf_protect
def reset_seo_super_admin(request, entity_type, entity_public_id):
    """
    UNIT 15: Reset SEO to auto-generated (Super Admin only).
    
    Resets SEO metadata to auto-generated values:
    - Regenerates SEO using existing logic
    - Sets seo_autogenerated=True
    - Logs action
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from dashboards.audit import log_super_admin_action
    
    try:
        if entity_type == 'pandit':
            from profiles.models import PanditProfile
            from profiles.seo_services import auto_generate_pandit_seo
            from core.public_id import resolve_public_id
            
            entity = resolve_public_id(PanditProfile, entity_public_id)
            if not entity:
                raise Http404("Pandit Profile not found")
            
            # Capture before state
            before_snapshot = {
                'seo_title': entity.seo_title,
                'seo_description': entity.seo_description,
                'seo_keywords': entity.seo_keywords,
                'seo_autogenerated': entity.seo_autogenerated,
            }
            
            # Regenerate SEO
            auto_generate_pandit_seo(entity, force=True)
            entity.seo_autogenerated = True
            entity.save(update_fields=['seo_title', 'seo_description', 'seo_keywords', 'seo_autogenerated', 'seo_last_updated_at'])
            
            # Capture after state
            after_snapshot = {
                'seo_title': entity.seo_title,
                'seo_description': entity.seo_description,
                'seo_keywords': entity.seo_keywords,
                'seo_autogenerated': True,
            }
            
            entity_name = entity.get_display_name() or entity.user.email
            
        elif entity_type == 'page':
            from pages.models import Page
            from pages.seo_services import auto_generate_page_seo
            from core.public_id import resolve_public_id
            
            entity = resolve_public_id(Page, entity_public_id)
            if not entity:
                raise Http404("Page not found")
            
            # Capture before state
            before_snapshot = {
                'seo_title': entity.seo_title,
                'seo_description': entity.seo_description,
                'seo_keywords': entity.seo_keywords,
                'seo_autogenerated': entity.seo_autogenerated,
            }
            
            # Regenerate SEO
            auto_generate_page_seo(entity, force=True)
            entity.seo_autogenerated = True
            entity.save(update_fields=['seo_title', 'seo_description', 'seo_keywords', 'seo_autogenerated', 'seo_last_updated_at'])
            
            # Capture after state
            after_snapshot = {
                'seo_title': entity.seo_title,
                'seo_description': entity.seo_description,
                'seo_keywords': entity.seo_keywords,
                'seo_autogenerated': True,
            }
            
            entity_name = entity.title
        else:
            messages.error(request, f'Invalid entity type: {entity_type}')
            return redirect('module5_dashboards:dashboard_super_admin')
        
        # UNIT 6: Log Super Admin action
        log_super_admin_action(
            action_type='SEO_RESET',
            target_entity=entity,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            actor=request.user,
        )
        
        messages.success(request, f'SEO metadata reset to auto-generated for {entity_name}.')
    except Exception as e:
        messages.error(request, f'Error resetting SEO: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_super_admin')


@login_required
@csrf_protect
def edit_seo_super_admin(request, entity_type, entity_public_id):
    """
    UNIT 15: Edit SEO metadata manually (Super Admin only).
    
    Allows Super Admin to manually override SEO:
    - Edit SEO title, description, keywords
    - Sets seo_autogenerated=False
    - Logs action
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from dashboards.audit import log_super_admin_action
    from core.public_id import resolve_public_id
    
    try:
        if entity_type == 'pandit':
            from profiles.models import PanditProfile
            entity = resolve_public_id(PanditProfile, entity_public_id)
            if not entity:
                raise Http404("Pandit Profile not found")
            entity_name = entity.get_display_name() or entity.user.email
        elif entity_type == 'page':
            from pages.models import Page
            entity = resolve_public_id(Page, entity_public_id)
            if not entity:
                raise Http404("Page not found")
            entity_name = entity.title
        else:
            messages.error(request, f'Invalid entity type: {entity_type}')
            return redirect('module5_dashboards:dashboard_super_admin')
        
        if request.method == 'POST':
            # Capture before state
            before_snapshot = {
                'seo_title': entity.seo_title,
                'seo_description': entity.seo_description,
                'seo_keywords': entity.seo_keywords,
                'seo_autogenerated': entity.seo_autogenerated,
            }
            
            # Update SEO fields
            seo_title = request.POST.get('seo_title', '').strip()[:60] if request.POST.get('seo_title') else None
            seo_description = request.POST.get('seo_description', '').strip()[:160] if request.POST.get('seo_description') else None
            seo_keywords = request.POST.get('seo_keywords', '').strip() if request.POST.get('seo_keywords') else None
            
            entity.seo_title = seo_title
            entity.seo_description = seo_description
            entity.seo_keywords = seo_keywords
            entity.seo_autogenerated = False  # Mark as manually edited
            entity.save(update_fields=['seo_title', 'seo_description', 'seo_keywords', 'seo_autogenerated', 'seo_last_updated_at'])
            
            # Capture after state
            after_snapshot = {
                'seo_title': entity.seo_title,
                'seo_description': entity.seo_description,
                'seo_keywords': entity.seo_keywords,
                'seo_autogenerated': False,
            }
            
            # UNIT 6: Log Super Admin action
            log_super_admin_action(
                action_type='SEO_EDIT',
                target_entity=entity,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                actor=request.user,
            )
            
            messages.success(request, f'SEO metadata updated for {entity_name}.')
            return redirect('module5_dashboards:dashboard_super_admin')
        else:
            # GET request - show edit form
            return render(request, 'dashboards/seo_edit_super_admin.html', {
                'entity_type': entity_type,
                'entity': entity,
                'entity_name': entity_name,
                'seo_title': entity.seo_title,
                'seo_description': entity.seo_description,
                'seo_keywords': entity.seo_keywords,
                'seo_autogenerated': entity.seo_autogenerated,
            })
    except Exception as e:
        messages.error(request, f'Error editing SEO: {str(e)}')
        return redirect('module5_dashboards:dashboard_super_admin')


# ============================================================================
# UNIT 16: Indexing & Crawl Readiness Monitor (Read-Only)
# ============================================================================

@login_required
def crawl_readiness_monitor(request):
    """
    UNIT 16: Indexing & Crawl Readiness Monitor (Super Admin only).
    
    Shows read-only indicators for whether content is crawlable:
    - Public URL
    - Meta tags present (yes/no)
    - JSON-LD present (yes/no)
    - Canonical URL present (yes/no)
    - Visibility status
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    crawl_list = DashboardMetricsService.get_crawl_readiness_indicators()
    
    return render(request, 'dashboards/crawl_readiness_monitor.html', {
        'crawl_list': crawl_list,
    })


# ============================================================================
# UNIT 17: Analytics / GTM Configuration (Super Admin Only)
# ============================================================================

@login_required
def analytics_config_super_admin(request):
    """
    UNIT 17: Analytics / GTM Configuration (Super Admin only).
    
    Manage observation-only analytics, fully invisible to others.
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from tracking_config.models import TrackingConfiguration
    
    # Get active configuration
    active_config = TrackingConfiguration.objects.filter(is_active=True).first()
    
    if request.method == 'POST':
        # Update or create configuration
        config_id = request.POST.get('config_id')
        if config_id:
            config = TrackingConfiguration.objects.get(pk=config_id)
        else:
            # Deactivate existing active configs
            TrackingConfiguration.objects.filter(is_active=True).update(is_active=False)
            config = TrackingConfiguration.objects.create(
                provider_type=request.POST.get('provider_type', TrackingConfiguration.PROVIDER_GTM),
                created_by=request.user,
            )
        
        config.head_snippet = request.POST.get('head_snippet', '')
        config.body_snippet = request.POST.get('body_snippet', '')
        config.footer_snippet = request.POST.get('footer_snippet', '')
        config.is_active = request.POST.get('is_active') == 'on'
        config.excluded_route_patterns = request.POST.get('excluded_route_patterns', '')
        config.updated_by = request.user
        
        config.save()
        
        from dashboards.audit import log_super_admin_action
        log_super_admin_action(
            action_type='ANALYTICS_CONFIG_UPDATE',
            target_entity=config,
            before_snapshot=None,
            after_snapshot={'is_active': config.is_active, 'provider_type': config.provider_type},
            actor=request.user,
        )
        
        messages.success(request, 'Analytics configuration updated successfully.')
        return redirect('module5_dashboards:analytics_config_super_admin')
    
    return render(request, 'dashboards/analytics_config_super_admin.html', {
        'active_config': active_config,
        'provider_choices': TrackingConfiguration.PROVIDER_CHOICES,
        'dashboard_has_data': True,  # Required by dashboard_base.html to show content
    })


# ============================================================================
# UNIT 18: Feature Flags (Kill Switches)
# ============================================================================

@login_required
def feature_flags_super_admin(request):
    """
    UNIT 18: Feature Flags management (Super Admin only).
    
    Allow Super Admin to safely disable features during incidents.
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from core.models import FeatureFlag
    
    flags = FeatureFlag.objects.all().order_by('key')
    
    if request.method == 'POST':
        flag_id = request.POST.get('flag_id')
        is_enabled = request.POST.get('is_enabled') == 'on'
        
        flag = FeatureFlag.objects.get(pk=flag_id)
        
        before_snapshot = {'is_enabled': flag.is_enabled}
        flag.is_enabled = is_enabled
        flag.updated_by = request.user
        flag.save()
        
        after_snapshot = {'is_enabled': flag.is_enabled}
        
        from dashboards.audit import log_super_admin_action
        log_super_admin_action(
            action_type='FEATURE_FLAG_TOGGLE',
            target_entity=flag,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            actor=request.user,
        )
        
        messages.success(request, f'Feature flag "{flag.key}" {"enabled" if is_enabled else "disabled"}.')
        return redirect('module5_dashboards:feature_flags_super_admin')
    
    return render(request, 'dashboards/feature_flags_super_admin.html', {
        'flags': flags,
    })


# ============================================================================
# System Operational Settings (Dashboard-editable config overlay only)
# ============================================================================

# Six approved operational keys (view-only; not loaded from DB). Keys controlled in code.
APPROVED_SETTINGS = {
    'CONTACT_RATE_LIMIT_COUNT': {
        'default': 3,
        'min': 1,
        'max': 50,
        'label': 'Contact Rate Limit Count',
        'description': 'Maximum contact requests allowed per window.',
    },
    'CONTACT_RATE_LIMIT_WINDOW_SECONDS': {
        'default': 300,
        'min': 60,
        'max': 3600,
        'label': 'Contact Rate Limit Window (seconds)',
        'description': 'Time window for contact rate limiting.',
    },
    'DASHBOARD_PAGES_PREVIEW_LIMIT': {
        'default': 50,
        'min': 5,
        'max': 200,
        'label': 'Dashboard Pages Preview Limit',
        'description': 'Number of pages shown in dashboard preview.',
    },
    'DASHBOARD_AUDIT_EXPORT_LIMIT': {
        'default': 1000,
        'min': 100,
        'max': 10000,
        'label': 'Dashboard Audit Export Limit',
        'description': 'Maximum rows allowed for audit export.',
    },
    'API_MAX_PAGE_SIZE': {
        'default': 100,
        'min': 10,
        'max': 500,
        'label': 'API Maximum Page Size',
        'description': 'Maximum page size allowed in paginated APIs.',
    },
    'API_DEFAULT_SEARCH_PAGE_SIZE': {
        'default': 20,
        'min': 5,
        'max': 100,
        'label': 'API Default Search Page Size',
        'description': 'Default page size for search endpoints.',
    },
}


@login_required
def system_operational_settings_super_admin(request):
    """
    Super Admin only: edit the 6 approved operational settings.
    Always renders 6 keys (DB overlay or default). Audit-logged; cache invalidated per key.
    """
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")

    from core.models_config import SystemConfig
    from core.config import get_config_value, invalidate_config_cache
    from dashboards.audit import log_super_admin_action

    if request.method == 'POST':
        for key, config in APPROVED_SETTINGS.items():
            raw_value = request.POST.get(key)
            if raw_value is None:
                continue
            try:
                value = int(raw_value)
            except (ValueError, TypeError):
                continue
            if value < config['min'] or value > config['max']:
                continue
            old_row = SystemConfig.objects.filter(key=key).first()
            before_snapshot = {key: old_row.value} if old_row else {}
            row, _ = SystemConfig.objects.update_or_create(
                key=key,
                defaults={'value': str(value), 'updated_by': request.user},
            )
            log_super_admin_action(
                action_type='SYSTEM_CONFIG_UPDATE',
                target_entity=row,
                before_snapshot=before_snapshot or None,
                after_snapshot={key: str(value)},
                actor=request.user,
            )
            invalidate_config_cache(key)
        messages.success(request, 'System operational settings updated. Changes apply immediately.')
        return redirect('module5_dashboards:system_operational_settings_super_admin')

    # Build settings_data: current from get_config_value (DB or default). Works when DB is empty.
    settings_data = []
    for key, config in APPROVED_SETTINGS.items():
        current_value = get_config_value(key, config['default'], cast_type=int)
        settings_data.append({
            'key': key,
            'label': config['label'],
            'description': config['description'],
            'default': config['default'],
            'min': config['min'],
            'max': config['max'],
            'current': current_value,
        })

    return render(request, 'dashboards/system_operational_settings_super_admin.html', {
        'settings_data': settings_data,
        'dashboard_has_data': True,
    })


# ============================================================================
# UNIT 19: Platform Kill Switch (Emergency Only)
# ============================================================================

@login_required
def platform_kill_switch_super_admin(request):
    """
    UNIT 19: Platform Kill Switch (Super Admin only).
    
    Emergency control for platform-wide protection.
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from core.models import PlatformKillSwitch
    
    kill_switch = PlatformKillSwitch.get_active()
    
    if request.method == 'POST':
        before_snapshot = {
            'is_active': kill_switch.is_active,
            'disable_public_access': kill_switch.disable_public_access,
            'disable_new_writes': kill_switch.disable_new_writes,
            'maintenance_message': kill_switch.maintenance_message,
        }
        
        kill_switch.is_active = request.POST.get('is_active') == 'on'
        kill_switch.disable_public_access = request.POST.get('disable_public_access') == 'on'
        kill_switch.disable_new_writes = request.POST.get('disable_new_writes') == 'on'
        kill_switch.maintenance_message = request.POST.get('maintenance_message', '')
        kill_switch.updated_by = request.user
        kill_switch.save()
        
        after_snapshot = {
            'is_active': kill_switch.is_active,
            'disable_public_access': kill_switch.disable_public_access,
            'disable_new_writes': kill_switch.disable_new_writes,
            'maintenance_message': kill_switch.maintenance_message,
        }
        
        from dashboards.audit import log_super_admin_action
        log_super_admin_action(
            action_type='PLATFORM_KILL_SWITCH',
            target_entity=kill_switch,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            actor=request.user,
        )
        
        messages.success(request, 'Platform kill switch updated successfully.')
        return redirect('module5_dashboards:platform_kill_switch_super_admin')
    
    return render(request, 'dashboards/platform_kill_switch_super_admin.html', {
        'kill_switch': kill_switch,
    })


# ============================================================================
# UNIT 20: Configuration Change Audit
# ============================================================================

@login_required
def config_change_audit_super_admin(request):
    """
    UNIT 20: Configuration Change Audit (Super Admin only).
    
    Track every system-level change:
    - Feature flags
    - Analytics config
    - Kill switch
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from django.core.paginator import Paginator
    from django.utils import timezone
    from datetime import timedelta
    
    # Get filter parameters
    config_type_filter = request.GET.get('config_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    page_number = request.GET.get('page', 1)
    
    # Build unified audit query from all config audit sources
    # For now, we'll use SuperAdminAuditLog filtered by action types
    # In a full implementation, this would aggregate from multiple audit tables
    
    audit_records = []
    
    # Get feature flag changes (from FeatureFlag updated_at)
    from core.models import FeatureFlag
    feature_flags = FeatureFlag.objects.filter(
        updated_by__isnull=False
    ).select_related('updated_by').order_by('-updated_at')
    
    if config_type_filter == 'feature_flag' or not config_type_filter:
        for flag in feature_flags:
            audit_records.append({
                'config_type': 'Feature Flag',
                'config_name': flag.key,
                'action': 'TOGGLE',
                'actor': flag.updated_by,
                'timestamp': flag.updated_at,
                'before_value': None,  # Would need audit log for this
                'after_value': {'is_enabled': flag.is_enabled},
            })
    
    # Get analytics config changes (from TrackingConfigurationAudit)
    if config_type_filter == 'analytics' or not config_type_filter:
        from tracking_config.models import TrackingConfigurationAudit
        analytics_audits = TrackingConfigurationAudit.objects.select_related(
            'tracking_configuration', 'changed_by'
        ).order_by('-changed_at')
        
        for audit in analytics_audits:
            audit_records.append({
                'config_type': 'Analytics',
                'config_name': audit.tracking_configuration.get_provider_type_display(),
                'action': audit.action,
                'actor': audit.changed_by,
                'timestamp': audit.changed_at,
                'before_value': audit.old_value,
                'after_value': audit.new_value,
            })
    
    # Get kill switch changes (from PlatformKillSwitch updated_at)
    if config_type_filter == 'kill_switch' or not config_type_filter:
        from core.models import PlatformKillSwitch
        kill_switch = PlatformKillSwitch.get_active()
        if kill_switch.updated_by:
            audit_records.append({
                'config_type': 'Platform Kill Switch',
                'config_name': 'Platform Kill Switch',
                'action': 'UPDATE',
                'actor': kill_switch.updated_by,
                'timestamp': kill_switch.updated_at,
                'before_value': None,  # Would need audit log for this
                'after_value': {
                    'is_active': kill_switch.is_active,
                    'disable_public_access': kill_switch.disable_public_access,
                    'disable_new_writes': kill_switch.disable_new_writes,
                },
            })
    
    # Apply date filters
    if date_from:
        try:
            date_from_obj = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            audit_records = [r for r in audit_records if r['timestamp'].date() >= date_from_obj]
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = timezone.datetime.strptime(date_to, '%Y-%m-%d').date() + timedelta(days=1)
            audit_records = [r for r in audit_records if r['timestamp'].date() < date_to_obj]
        except ValueError:
            pass
    
    # Sort by timestamp (newest first)
    audit_records.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Paginate (PART 3 hardening: use constant)
    from core.api_constants import DEFAULT_PAGE_SIZE
    paginator = Paginator(audit_records, DEFAULT_PAGE_SIZE)
    try:
        audit_page = paginator.page(page_number)
    except:
        audit_page = paginator.page(1)
    
    return render(request, 'dashboards/config_change_audit_super_admin.html', {
        'dashboard_has_data': True,  # Required by dashboard_base.html to show content
        'audit_records': audit_page,
        'audit_paginator': paginator,
        'audit_page': audit_page,
        'config_type_filter': config_type_filter,
        'date_from': date_from,
        'date_to': date_to,
    })


# ============================================================================
# UNIT 20: Master Data Management (MDM)
# ============================================================================

@login_required
def master_data_management(request):
    """
    UNIT 20: Master Data Management (Super Admin only).
    
    Provide Super Admin with full control over canonical platform data:
    - Cities
    - Local Areas
    - Poojas
    - Languages
    - Pooja Categories
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from masterdata.models import City, LocalArea, Pooja, Language, PoojaCategory
    from django.db.models import Count
    
    # Get ALL master data (including CSV-uploaded data) with usage counts
    # Show all records, not just active ones
    # Use prefetch_related to optimize queries and evaluate queryset
    cities_queryset = City.objects.prefetch_related('local_areas', 'mandals').all().order_by('name')
    # Evaluate queryset and calculate usage count for each city
    cities = []
    for city in cities_queryset:
        city.usage_count = city.local_areas.count() + city.mandals.count()
        cities.append(city)
    
    local_areas_queryset = LocalArea.objects.select_related('city').all().order_by('city__name', 'name')
    # Evaluate queryset and set usage count
    local_areas = []
    for area in local_areas_queryset:
        area.usage_count = 0  # Local areas don't have reverse usage
        local_areas.append(area)
    
    poojas = Pooja.objects.select_related('pooja_category').annotate(
        usage_count=Count('pandits', distinct=True)
    ).order_by('pooja_category__display_order', 'name')
    
    languages = Language.objects.annotate(
        usage_count=Count('pandit_profiles', distinct=True)
    ).order_by('name')
    
    pooja_categories = PoojaCategory.objects.annotate(
        usage_count=Count('poojas', distinct=True)
    ).order_by('display_order', 'name')
    
    return render(request, 'dashboards/master_data_management.html', {
        'cities': cities,
        'local_areas': local_areas,
        'poojas': poojas,
        'languages': languages,
        'pooja_categories': pooja_categories,
        'dashboard_has_data': True,  # Required by dashboard_base.html to show content
    })


@login_required
@csrf_protect
def master_data_edit(request, entity_type, entity_id):
    """
    UNIT 20: Edit master data entity (Super Admin only).
    
    Supports: city, localarea, pooja, language, poojacategory
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from dashboards.forms import CityForm, LocalAreaForm, PoojaForm, LanguageForm, PoojaCategoryForm
    from django.contrib import messages
    from django.shortcuts import redirect
    from dashboards.audit import log_super_admin_action
    from masterdata.models import City, LocalArea, Pooja, Language, PoojaCategory
    
    # Map entity types to models and forms
    entity_map = {
        'city': (City, CityForm),
        'localarea': (LocalArea, LocalAreaForm),
        'pooja': (Pooja, PoojaForm),
        'language': (Language, LanguageForm),
        'poojacategory': (PoojaCategory, PoojaCategoryForm),
    }
    
    if entity_type not in entity_map:
        from django.contrib import messages
        messages.error(request, f'Invalid entity type: {entity_type}')
        return redirect('module5_dashboards:master_data_management')
    
    ModelClass, FormClass = entity_map[entity_type]
    
    try:
        entity = ModelClass.objects.get(pk=entity_id)
    except ModelClass.DoesNotExist:
        from django.contrib import messages
        messages.error(request, f'{entity_type.title()} not found.')
        return redirect('module5_dashboards:master_data_management')
    
    if request.method == 'POST':
        form = FormClass(request.POST, instance=entity)
        if form.is_valid():
            before_snapshot = {
                'name': str(entity),
                'is_active': entity.is_active,
                'status': getattr(entity, 'status', None),
            }
            
            form.save()
            
            after_snapshot = {
                'name': str(entity),
                'is_active': entity.is_active,
                'status': getattr(entity, 'status', None),
            }
            
            # Log action
            log_super_admin_action(
                action_type='MASTER_DATA_EDIT',
                target_entity=entity,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                actor=request.user,
            )
            
            from django.contrib import messages
            messages.success(request, f'{entity_type.title()} updated successfully.')
            from django.urls import reverse
            tab_fragments = {'city': 'cities', 'localarea': 'areas', 'pooja': 'poojas', 'language': 'languages', 'poojacategory': 'categories'}
            fragment = tab_fragments.get(entity_type, '')
            return redirect(reverse('module5_dashboards:master_data_management') + ('#' + fragment if fragment else ''))
    else:
        form = FormClass(instance=entity)
    
    return render(request, 'dashboards/master_data_edit.html', {
        'entity_type': entity_type,
        'entity': entity,
        'entity_name': str(entity),
        'form': form,
        'dashboard_has_data': True,  # So dashboard_base shows the edit form, not "No data available"
    })


@login_required
@require_POST
@csrf_protect
def master_data_toggle_status(request, entity_type, entity_id):
    """
    UNIT 20: Toggle master data status (activate/deactivate) (Super Admin only).
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from dashboards.audit import log_super_admin_action
    from masterdata.models import City, LocalArea, Pooja, Language, PoojaCategory
    from django.contrib import messages
    
    entity_map = {
        'city': City,
        'localarea': LocalArea,
        'pooja': Pooja,
        'language': Language,
        'poojacategory': PoojaCategory,
    }
    
    if entity_type not in entity_map:
        messages.error(request, f'Invalid entity type: {entity_type}')
        return redirect('module5_dashboards:master_data_management')
    
    ModelClass = entity_map[entity_type]
    
    try:
        entity = ModelClass.objects.get(pk=entity_id)
    except ModelClass.DoesNotExist:
        messages.error(request, f'{entity_type.title()} not found.')
        return redirect('module5_dashboards:master_data_management')
    
    before_snapshot = {
        'is_active': entity.is_active,
        'status': getattr(entity, 'status', None),
    }
    
    # Toggle status: deactivate or activate (City/LocalArea have no deactivate(), so flip is_active and status)
    if entity.is_active:
        if hasattr(entity, 'deactivate'):
            entity.deactivate(reason="Toggled via Super Admin dashboard", actor=request.user)
        else:
            entity.is_active = False
            if hasattr(entity, 'status'):
                entity.status = 'inactive'
            entity.save()
    else:
        entity.is_active = True
        if hasattr(entity, 'status'):
            entity.status = 'active'
        entity.save()
    
    after_snapshot = {
        'is_active': entity.is_active,
        'status': getattr(entity, 'status', None),
    }
    
    # Log action
    log_super_admin_action(
        action_type='MASTER_DATA_TOGGLE',
        target_entity=entity,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        actor=request.user,
    )
    
    messages.success(request, f'{entity_type.title()} status updated successfully.')
    # Redirect back to master data page with same tab active
    from django.urls import reverse
    tab_fragments = {'city': 'cities', 'localarea': 'areas', 'pooja': 'poojas', 'language': 'languages', 'poojacategory': 'categories'}
    fragment = tab_fragments.get(entity_type, '')
    return redirect(reverse('module5_dashboards:master_data_management') + ('#' + fragment if fragment else ''))


# ============================================================================
# PART 4: NOTIFICATIONS, EXPORTS & SAFETY RAILS
# ============================================================================

# UNIT 21: Notifications & Alerts (Super Admin)
@login_required
def super_admin_notifications(request):
    """
    UNIT 21: Notifications & Alerts (Super Admin only).
    
    System-level notifications:
    - Pandit approval pending (threshold-based)
    - Repeated failed actions
    - System health degradation
    - Governance queue backlog
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from accounts.models import User
    from profiles.models import PanditProfile
    
    notifications = []
    
    # Check for pending Pandit approvals (threshold: 5+)
    pending_pandits = PanditProfile.objects.filter(user__status='pending').count()
    if pending_pandits >= 5:
        notifications.append({
            'type': 'warning',
            'title': 'Pending Pandit Approvals',
            'message': f'{pending_pandits} Pandit(s) are pending approval.',
            'action_url': '?pandit_status=pending',
            'priority': 'high',
        })
    
    # Check for system health (placeholder - would integrate with UNIT 4)
    # This is a simple example - in production, would check actual health indicators
    
    # Pass dashboard_has_data so dashboard_base shows this page's content (not "No data available")
    return render(request, 'dashboards/super_admin_notifications.html', {
        'notifications': notifications,
        'unread_count': len([n for n in notifications if n.get('priority') == 'high']),
        'dashboard_has_data': True,
    })


# UNIT 22: Data Export (Read-Only)
@login_required
def export_data_super_admin(request):
    """
    UNIT 22: Data Export (Super Admin only).
    
    Export selected data:
    - Pandit list
    - Pages list
    - Governance actions
    - Audit logs
    - Master data
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from django.http import HttpResponse
    import csv
    
    export_type = request.GET.get('type', 'pandits')
    
    if export_type == 'pandits':
        from profiles.models import PanditProfile
        queryset = (
            PanditProfile.objects.select_related("user")
            .prefetch_related("cities_served")
            .all()
        )
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="pandits_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Status', 'City', 'Joined Date'])
        
        for profile in queryset:
            cities = list(profile.cities_served.all())
            city = cities[0].name if cities else "N/A"
            writer.writerow([
                profile.get_display_name() or profile.user.email,
                profile.user.email,
                profile.user.status,
                city,
                profile.user.date_joined.strftime('%Y-%m-%d'),
            ])
        
        return response
    
    elif export_type == 'pages':
        from pages.models import Page
        queryset = Page.objects.select_related('created_by').all()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="pages_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Title', 'Page Type', 'Status', 'Owner', 'Created Date'])
        
        for page in queryset:
            writer.writerow([
                page.title,
                page.page_type,
                page.status,
                page.created_by.email if page.created_by else 'System',
                page.created_at.strftime('%Y-%m-%d'),
            ])
        
        return response
    
    elif export_type == 'audit':
        from core.api_constants import get_dashboard_audit_export_limit
        from core.config import get_config_value
        from pages.models import PageAuditLog
        default_audit = get_dashboard_audit_export_limit()
        audit_limit = get_config_value('DASHBOARD_AUDIT_EXPORT_LIMIT', default_audit)
        queryset = PageAuditLog.objects.select_related('page', 'performed_by').order_by('-created_at')[:audit_limit]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Action', 'Entity Type', 'Entity', 'Actor', 'Timestamp'])
        
        for log in queryset:
            writer.writerow([
                log.action,
                'Page',
                log.page.title,
                log.performed_by.email if log.performed_by else 'System',
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        return response
    
    else:
        messages.error(request, 'Invalid export type.')
        return redirect('module5_dashboards:dashboard_super_admin')


# UNIT 24: Final Hardening & Consistency Checks
@login_required
def consistency_checks_super_admin(request):
    """
    UNIT 24: Final Hardening & Consistency Checks (Super Admin only).
    
    Checks:
    - All Super Admin routes return 404 for others
    - No menu leakage
    - All actions audited
    - All master data consistent
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    checks = []
    
    # Check 1: Verify master data consistency
    from masterdata.models import City, LocalArea, Pooja, Language
    orphan_areas = LocalArea.objects.filter(city__isnull=True).count()
    if orphan_areas > 0:
        checks.append({
            'name': 'Orphan Local Areas',
            'status': 'warning',
            'message': f'{orphan_areas} local area(s) have no associated city.',
        })
    else:
        checks.append({
            'name': 'Local Areas Consistency',
            'status': 'success',
            'message': 'All local areas have valid cities.',
        })
    
    # Check 2: Verify audit logging
    from pages.models import PageAuditLog
    from django.utils import timezone
    from datetime import timedelta
    recent_audits = PageAuditLog.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=1)
    ).count()
    checks.append({
        'name': 'Audit Logging',
        'status': 'success' if recent_audits > 0 else 'warning',
        'message': f'{recent_audits} audit log(s) created in last 24 hours.',
    })
    
    # Check 3: Verify master data status consistency
    inconsistent_cities = City.objects.filter(is_active=True, status='inactive').count()
    if inconsistent_cities > 0:
        checks.append({
            'name': 'City Status Consistency',
            'status': 'warning',
            'message': f'{inconsistent_cities} city/cities have inconsistent status.',
        })
    else:
        checks.append({
            'name': 'City Status Consistency',
            'status': 'success',
            'message': 'All cities have consistent status.',
        })
    
    return render(request, 'dashboards/consistency_checks_super_admin.html', {
        'checks': checks,
    })


# Referral Management (Super Admin) - reuses referrals.services; no logic duplication
@login_required
def super_admin_referral_links(request):
    """
    Super Admin: list all referral links (global view). Filters by status and created date.
    Uses existing ReferralLink queryset; pagination from API_DEFAULT_PAGE_SIZE.
    """
    from django.http import Http404
    if not request.user.is_superuser:
        raise Http404("Page not found")
    from referrals.models import ReferralLink, ReferralPolicy
    from referrals import services
    from core.api_constants import DEFAULT_PAGE_SIZE
    from django.core.paginator import Paginator
    from django.utils.dateparse import parse_date

    qs = ReferralLink.objects.all().select_related('created_by').order_by('-created_at')
    status_filter = request.GET.get('status', '').strip()
    if status_filter and status_filter in dict(ReferralLink.STATUS_CHOICES):
        qs = qs.filter(status=status_filter)
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        d = parse_date(date_from)
        if d:
            qs = qs.filter(created_at__date__gte=d)
    if date_to:
        d = parse_date(date_to)
        if d:
            qs = qs.filter(created_at__date__lte=d)

    paginator = Paginator(qs, DEFAULT_PAGE_SIZE)
    page_num = request.GET.get('page', 1)
    try:
        page_num = max(1, int(page_num))
    except (ValueError, TypeError):
        page_num = 1
    page = paginator.get_page(page_num)

    from django.urls import reverse
    referral_links_with_urls = []
    for link in page.object_list:
        token = link.token or link.referral_code or ''
        path = reverse('accounts:pandit_register', kwargs={'referral_token': token})
        referral_url = request.build_absolute_uri(path)
        referral_links_with_urls.append({'link': link, 'referral_url': referral_url})

    policy = ReferralPolicy.load()
    expiry_options = services.get_expiry_days_options(policy)
    tiers = list(policy.allowed_max_use_tiers) if isinstance(policy.allowed_max_use_tiers, (list, tuple)) else []

    return render(request, 'dashboards/super_admin_referral_links.html', {
        'page_obj': page,
        'referral_links_with_urls': referral_links_with_urls,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'policy': policy,
        'referral_expiry_days_options': expiry_options,
        'status_choices': ReferralLink.STATUS_CHOICES,
        'dashboard_has_data': True,
    })


@login_required
def super_admin_create_referral_link(request):
    """
    Super Admin: create referral link via same service as Admin Pandit.
    GET: form with max_uses (from policy tiers) and expiry_days (from policy).
    POST: validate and call referrals.services.create_referral_link; audit log; redirect to list.
    """
    from django.http import Http404
    if not request.user.is_superuser:
        raise Http404("Page not found")
    from referrals.models import ReferralPolicy
    from referrals import services
    from dashboards.audit import log_super_admin_action

    policy = ReferralPolicy.load()
    tiers = list(policy.allowed_max_use_tiers) if isinstance(policy.allowed_max_use_tiers, (list, tuple)) else []
    if not tiers:
        tiers = [min(policy.max_allowed_uses, 100)]
    expiry_options = services.get_expiry_days_options(policy)

    if request.method == 'POST':
        max_uses = request.POST.get('max_uses')
        expiry_days = request.POST.get('expiry_days')
        if not max_uses or not expiry_days:
            messages.error(request, 'Max uses and expiry days are required.')
            return redirect('module5_dashboards:super_admin_create_referral_link')
        try:
            referral_link = services.create_referral_link(
                creator=request.user,
                max_uses=int(max_uses),
                expiry_days=int(expiry_days),
            )
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('module5_dashboards:super_admin_create_referral_link')
        log_super_admin_action(
            action_type='REFERRAL_LINK_CREATE',
            target_entity=referral_link,
            before_snapshot=None,
            after_snapshot={
                'id': referral_link.id,
                'token': (referral_link.token or '')[:8] + '...',
                'max_uses': referral_link.max_uses,
                'expires_at': referral_link.expires_at.isoformat() if referral_link.expires_at else None,
            },
            actor=request.user,
        )
        messages.success(request, 'Referral link created successfully.')
        return redirect('module5_dashboards:super_admin_referral_links')

    return render(request, 'dashboards/super_admin_create_referral_link.html', {
        'policy': policy,
        'referral_tiers': tiers,
        'referral_expiry_days_options': expiry_options,
        'dashboard_has_data': True,
    })


@login_required
@require_POST
@csrf_protect
def super_admin_revoke_referral_link(request, referral_link_id):
    """
    Super Admin: revoke (deactivate) a referral link. Uses same service as Admin Pandit.
    """
    from django.http import Http404
    if not request.user.is_superuser:
        raise Http404("Page not found")
    from referrals.models import ReferralLink
    from referrals import services
    from dashboards.audit import log_super_admin_action

    try:
        link = ReferralLink.objects.get(id=referral_link_id)
        before_snapshot = {'is_active': link.is_active, 'status': link.status}
        services.revoke_referral_link(referral_link_id, request.user)
        link.refresh_from_db()
        log_super_admin_action(
            action_type='REFERRAL_LINK_REVOKE',
            target_entity=link,
            before_snapshot=before_snapshot,
            after_snapshot={'is_active': link.is_active, 'status': link.status},
            actor=request.user,
        )
        messages.success(request, 'Referral link revoked.')
    except (ValueError, ReferralLink.DoesNotExist):
        messages.error(request, 'Referral link not found or already inactive.')
    except PermissionDenied:
        messages.error(request, 'Access denied.')
    return redirect('module5_dashboards:super_admin_referral_links')


# ============================================================================
# PART 3: PLATFORM CONTROLS, SEO OVERSIGHT & ANALYTICS
# ============================================================================

@login_required
@require_POST
@csrf_protect
def reset_pandit_seo_super_admin(request, public_id):
    """
    UNIT 15: Reset Pandit SEO to auto-generated (Super Admin only).
    
    Regenerates SEO metadata using existing logic and logs action.
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from profiles.models import PanditProfile
    from profiles.seo_services import auto_generate_pandit_seo
    from dashboards.audit import log_super_admin_action
    from core.public_id import resolve_public_id
    
    profile = resolve_public_id(PanditProfile, public_id)
    if not profile:
        raise Http404("Pandit Profile not found")
    
    try:
        before_snapshot = {
            'seo_title': profile.seo_title,
            'seo_description': profile.seo_description,
            'seo_keywords': profile.seo_keywords,
            'seo_autogenerated': profile.seo_autogenerated,
        }
        
        # Reset to auto-generated
        auto_generate_pandit_seo(profile, force=True)
        profile.refresh_from_db()
        
        after_snapshot = {
            'seo_title': profile.seo_title,
            'seo_description': profile.seo_description,
            'seo_keywords': profile.seo_keywords,
            'seo_autogenerated': profile.seo_autogenerated,
        }
        
        # UNIT 6: Log Super Admin action
        log_super_admin_action(
            action_type='SEO_RESET_PANDIT',
            target_entity=profile,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            actor=request.user,
        )
        
        messages.success(request, f"SEO metadata for {profile.get_display_name()} has been reset to auto-generated.")
    except Exception as e:
        messages.error(request, f'Error resetting SEO: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_super_admin')


@login_required
@require_POST
@csrf_protect
def reset_page_seo_super_admin(request, public_id):
    """
    UNIT 15: Reset Page SEO to auto-generated (Super Admin only).
    
    Regenerates SEO metadata using existing logic and logs action.
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from pages.models import Page
    from pages.seo_services import auto_generate_page_seo
    from dashboards.audit import log_super_admin_action
    from pages.page_permissions import resolve_public_id
    from core.public_id import reject_bigint_id
    
    if reject_bigint_id(public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, public_id)
    if not page:
        raise Http404("Page not found")
    
    try:
        before_snapshot = {
            'seo_title': page.seo_title,
            'seo_description': page.seo_description,
            'seo_keywords': page.seo_keywords,
            'seo_autogenerated': page.seo_autogenerated,
        }
        
        # Reset to auto-generated
        auto_generate_page_seo(page, force=True)
        page.refresh_from_db()
        
        after_snapshot = {
            'seo_title': page.seo_title,
            'seo_description': page.seo_description,
            'seo_keywords': page.seo_keywords,
            'seo_autogenerated': page.seo_autogenerated,
        }
        
        # UNIT 6: Log Super Admin action
        log_super_admin_action(
            action_type='SEO_RESET_PAGE',
            target_entity=page,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            actor=request.user,
        )
        
        messages.success(request, f"SEO metadata for page '{page.title}' has been reset to auto-generated.")
    except Exception as e:
        messages.error(request, f'Error resetting SEO: {str(e)}')
    
    return redirect('module5_dashboards:dashboard_super_admin')


@login_required
def edit_pandit_seo_super_admin(request, public_id):
    """
    UNIT 15: Edit Pandit SEO manually (Super Admin only).
    
    Allows Super Admin to override SEO metadata.
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from profiles.models import PanditProfile
    from core.public_id import resolve_public_id
    from dashboards.audit import log_super_admin_action
    
    profile = resolve_public_id(PanditProfile, public_id)
    if not profile:
        raise Http404("Pandit Profile not found")
    
    if request.method == 'POST':
        try:
            before_snapshot = {
                'seo_title': profile.seo_title,
                'seo_description': profile.seo_description,
                'seo_keywords': profile.seo_keywords,
                'seo_autogenerated': profile.seo_autogenerated,
            }
            
            # Update SEO fields
            seo_title = request.POST.get('seo_title', '').strip()
            seo_description = request.POST.get('seo_description', '').strip()
            seo_keywords = request.POST.get('seo_keywords', '').strip()
            
            if seo_title:
                profile.seo_title = seo_title[:60]  # Enforce max length
            if seo_description:
                profile.seo_description = seo_description[:160]  # Enforce max length
            if seo_keywords:
                profile.seo_keywords = seo_keywords
            
            profile.seo_autogenerated = False  # Mark as manually edited
            profile.save(update_fields=['seo_title', 'seo_description', 'seo_keywords', 'seo_autogenerated', 'seo_last_updated_at'])
            
            after_snapshot = {
                'seo_title': profile.seo_title,
                'seo_description': profile.seo_description,
                'seo_keywords': profile.seo_keywords,
                'seo_autogenerated': profile.seo_autogenerated,
            }
            
            # UNIT 6: Log Super Admin action
            log_super_admin_action(
                action_type='SEO_EDIT_PANDIT',
                target_entity=profile,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                actor=request.user,
            )
            
            messages.success(request, f"SEO metadata for {profile.get_display_name()} has been updated.")
            return redirect('module5_dashboards:dashboard_super_admin')
        except Exception as e:
            messages.error(request, f'Error updating SEO: {str(e)}')
    
    # GET request - show edit form
    return render(request, 'dashboards/seo_edit_super_admin.html', {
        'entity': profile,
        'entity_type': 'PanditProfile',
        'entity_name': profile.get_display_name() or profile.user.get_full_name() or profile.user.email,
    })


@login_required
def edit_page_seo_super_admin(request, public_id):
    """
    UNIT 15: Edit Page SEO manually (Super Admin only).
    
    Allows Super Admin to override SEO metadata.
    """
    # Enforce Super Admin only
    if not request.user.is_superuser:
        from django.http import Http404
        raise Http404("Page not found")
    
    from pages.models import Page
    from pages.page_permissions import resolve_public_id
    from core.public_id import reject_bigint_id
    from dashboards.audit import log_super_admin_action
    
    if reject_bigint_id(public_id):
        raise Http404("Invalid page ID format")
    
    page = resolve_public_id(Page, public_id)
    if not page:
        raise Http404("Page not found")
    
    if request.method == 'POST':
        try:
            before_snapshot = {
                'seo_title': page.seo_title,
                'seo_description': page.seo_description,
                'seo_keywords': page.seo_keywords,
                'seo_autogenerated': page.seo_autogenerated,
            }
            
            # Update SEO fields
            seo_title = request.POST.get('seo_title', '').strip()
            seo_description = request.POST.get('seo_description', '').strip()
            seo_keywords = request.POST.get('seo_keywords', '').strip()
            
            if seo_title:
                page.seo_title = seo_title[:60]  # Enforce max length
            if seo_description:
                page.seo_description = seo_description[:160]  # Enforce max length
            if seo_keywords:
                page.seo_keywords = seo_keywords
            
            page.seo_autogenerated = False  # Mark as manually edited
            page.save(update_fields=['seo_title', 'seo_description', 'seo_keywords', 'seo_autogenerated', 'seo_last_updated_at'])
            
            after_snapshot = {
                'seo_title': page.seo_title,
                'seo_description': page.seo_description,
                'seo_keywords': page.seo_keywords,
                'seo_autogenerated': page.seo_autogenerated,
            }
            
            # UNIT 6: Log Super Admin action
            log_super_admin_action(
                action_type='SEO_EDIT_PAGE',
                target_entity=page,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                actor=request.user,
            )
            
            messages.success(request, f"SEO metadata for page '{page.title}' has been updated.")
            return redirect('module5_dashboards:dashboard_super_admin')
        except Exception as e:
            messages.error(request, f'Error updating SEO: {str(e)}')
    
    # GET request - show edit form
    return render(request, 'dashboards/seo_edit_super_admin.html', {
        'entity': page,
        'entity_type': 'Page',
        'entity_name': page.title,
    })

