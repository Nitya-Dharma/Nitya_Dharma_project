"""
Analytics API Views

Read-only internal APIs for dashboard consumption (Module 5).
All outputs are aggregated and privacy-safe.

SECURITY NOTE:
Analytics endpoints are admin-protected and read-only.
If converted to write endpoints in future,
CSRF or token-based protection must be enforced.
"""

import logging
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Count
from core.api_constants import MAX_PAGE_SIZE
from analytics.models import AnalyticsEvent, AnalyticsAccessLog
from analytics.permissions import CanAccessAnalytics
from analytics.audit import log_analytics_access

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def analytics_events_list(request):
    """
    List analytics events with pagination.
    
    Only admins can access.
    """
    if not request.user.is_authenticated or not CanAccessAnalytics.can_access(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Log access
    log_analytics_access(
        user=request.user,
        access_type='api_query',
        filters_applied=request.GET.dict(),
    )
    
    # Get queryset
    events = AnalyticsEvent.objects.all()
    
    # Filter by event category
    category = request.GET.get('category', None)
    if category:
        events = events.filter(event_category=category)
    
    # Filter by event name
    event_name = request.GET.get('event_name', None)
    if event_name:
        events = events.filter(event_name=event_name)
    
    # Filter by date range
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)
    
    if start_date:
        try:
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            events = events.filter(timestamp__gte=start)
        except (ValueError, AttributeError):
            pass
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            events = events.filter(timestamp__lte=end)
        except (ValueError, AttributeError):
            pass
    
    # Pagination (cap per_page to prevent abuse)
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))
    if per_page < 1:
        per_page = 20
    if per_page > MAX_PAGE_SIZE:
        per_page = MAX_PAGE_SIZE
    paginator = Paginator(events.order_by('-timestamp'), per_page)
    
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    # Serialize
    events_data = [
        {
            'id': event.id,
            'event_name': event.event_name,
            'event_category': event.event_category,
            'metadata': event.metadata,
            'timestamp': event.timestamp.isoformat(),
            'created_at': event.created_at.isoformat(),
        }
        for event in page_obj
    ]
    
    return JsonResponse({
        'results': events_data,
        'count': paginator.count,
        'page': page,
        'per_page': per_page,
        'total_pages': paginator.num_pages,
    })


@require_http_methods(["GET"])
def analytics_aggregated(request):
    """
    Get aggregated analytics data for dashboards.
    
    Returns event counts grouped by event name and date.
    """
    if not request.user.is_authenticated or not CanAccessAnalytics.can_access(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Log access
    log_analytics_access(
        user=request.user,
        access_type='dashboard_aggregation',
        filters_applied=request.GET.dict(),
    )
    
    # Get date range (default: last 30 days)
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Aggregate events
    events = AnalyticsEvent.objects.filter(
        timestamp__gte=start_date
    ).values(
        'event_name',
        'event_category'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Format response
    aggregated_data = [
        {
            'event_name': event['event_name'],
            'event_category': event['event_category'],
            'count': event['count'],
            'date': timezone.now().date().isoformat(),
        }
        for event in events
    ]
    
    return JsonResponse({'results': aggregated_data})


@require_http_methods(["GET"])
def analytics_summary(request):
    """
    Get analytics summary statistics.
    
    Returns high-level metrics for dashboards.
    """
    if not request.user.is_authenticated or not CanAccessAnalytics.can_access(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Log access
    log_analytics_access(
        user=request.user,
        access_type='dashboard_summary',
    )
    
    # Get date range (default: last 30 days)
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Calculate summary
    total_events = AnalyticsEvent.objects.filter(
        timestamp__gte=start_date
    ).count()
    
    events_by_category = AnalyticsEvent.objects.filter(
        timestamp__gte=start_date
    ).values('event_category').annotate(
        count=Count('id')
    )
    
    events_by_name = AnalyticsEvent.objects.filter(
        timestamp__gte=start_date
    ).values('event_name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]  # Top 10 events
    
    return JsonResponse({
        'total_events': total_events,
        'events_by_category': {e['event_category']: e['count'] for e in events_by_category},
        'top_events': {e['event_name']: e['count'] for e in events_by_name},
        'period_days': days,
    })


@require_http_methods(["GET"])
def analytics_access_logs_list(request):
    """
    List analytics access logs with pagination.
    
    Only admins can access. Used for audit trail visibility.
    """
    if not request.user.is_authenticated or not CanAccessAnalytics.can_access(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Log access (meta-audit)
    log_analytics_access(
        user=request.user,
        access_type='audit_log_view',
    )
    
    # Get queryset
    logs = AnalyticsAccessLog.objects.all().order_by('-accessed_at')
    
    # Pagination (cap per_page to prevent abuse)
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    try:
        per_page = int(request.GET.get('per_page', 20))
    except (ValueError, TypeError):
        per_page = 20
    if per_page < 1:
        per_page = 20
    if per_page > MAX_PAGE_SIZE:
        per_page = MAX_PAGE_SIZE
    paginator = Paginator(logs, per_page)
    
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    # Serialize
    logs_data = [
        {
            'id': log.id,
            'accessed_by_email': log.accessed_by.email,
            'access_type': log.access_type,
            'filters_applied': log.filters_applied,
            'accessed_at': log.accessed_at.isoformat(),
        }
        for log in page_obj
    ]
    
    return JsonResponse({
        'results': logs_data,
        'count': paginator.count,
        'page': page,
        'per_page': per_page,
        'total_pages': paginator.num_pages,
    })
