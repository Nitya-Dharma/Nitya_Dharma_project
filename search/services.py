"""
Search Service

Task 7.13: Search Query Logic
Task 7.15: Search Safety, Validation & Rate Limit Hooks

Service layer for search functionality.
Read-only queries, no mutations, no side effects.
"""

import logging
from typing import Optional, Tuple
from django.db.models import Q
from django.contrib.auth import get_user_model
from profiles.models import PanditProfile
from masterdata.models import City, LocalArea, Pooja

User = get_user_model()
logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for search operations.
    
    All methods are read-only.
    No mutations, no side effects, no business logic.
    """
    
    @staticmethod
    def validate_search_params(
        city_id: Optional[int] = None,
        area_id: Optional[int] = None,
        pooja_id: Optional[int] = None,
        day_of_week: Optional[int] = None,
        specific_date: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate search parameters.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate city_id
        city = None
        if city_id is not None:
            try:
                city = City.objects.get(id=city_id, is_active=True)
            except City.DoesNotExist:
                return False, f"Invalid city_id: {city_id}"
        
        # Validate area_id
        if area_id is not None:
            try:
                area = LocalArea.objects.get(id=area_id, is_active=True)
                # If city_id is also provided, validate area belongs to city
                if city_id is not None and area.city_id != city_id:
                    return False, f"Area {area_id} does not belong to city {city_id}"
            except LocalArea.DoesNotExist:
                return False, f"Invalid area_id: {area_id}"
        
        # Validate pooja_id
        if pooja_id is not None:
            try:
                Pooja.objects.get(id=pooja_id, is_active=True)
            except Pooja.DoesNotExist:
                return False, f"Invalid pooja_id: {pooja_id}"
        
        # Validate day_of_week
        if day_of_week is not None:
            if day_of_week < 0 or day_of_week > 6:
                return False, "day_of_week must be between 0 and 6 (Monday=0, Sunday=6)"
        
        # Validate specific_date format (basic check)
        if specific_date is not None:
            from django.utils.dateparse import parse_date
            parsed_date = parse_date(specific_date)
            if parsed_date is None:
                return False, "Invalid specific_date format. Use YYYY-MM-DD"
        
        return True, ""
    
    @staticmethod
    def search_pandits(
        city_id: Optional[int] = None,
        area_id: Optional[int] = None,
        pooja_id: Optional[int] = None,
        day_of_week: Optional[int] = None,
        specific_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        exclude_fully_blocked: bool = True,
        enable_call: Optional[bool] = None,
        enable_whatsapp: Optional[bool] = None
    ):
        """
        Search for Pandits based on criteria.
        
        Returns:
            QuerySet of User objects with role='pandit' and status='active'
        
        Note:
            - Returns User objects, not PanditProfile objects
            - Caller should convert to PanditProfile if needed
            - Read-only query, no mutations
        """
        # TASK 19: Base queryset: Active Pandits only (visibility enforced at query time)
        # Database is authoritative - never show deactivated/inactive entities
        # Index is derived, not truth - filtering always applied before returning results
        queryset = User.objects.filter(
            role='pandit',
            status='active',  # TASK 19: Only active status
            is_active=True,   # TASK 19: Only active accounts
            # TASK 19: Exclude deactivated users explicitly
        ).exclude(
            status='deactivated'
        ).exclude(
            status='rejected'  # TASK 19: Exclude rejected users
        ).select_related('pandit_profile').prefetch_related(
            'pandit_profile__cities_served',
            'pandit_profile__areas_served',
            'pandit_profile__poojas_performed'
        )
        
        # Filter by city
        if city_id:
            queryset = queryset.filter(
                pandit_profile__cities_served__id=city_id
            ).distinct()
        
        # Filter by area
        if area_id:
            queryset = queryset.filter(
                pandit_profile__areas_served__id=area_id
            ).distinct()
        
        # Filter by pooja
        if pooja_id:
            queryset = queryset.filter(
                pandit_profile__poojas_performed__id=pooja_id
            ).distinct()
        
        # Filter by availability (day_of_week)
        if day_of_week is not None:
            from availability.models import Availability
            queryset = queryset.filter(
                pandit_profile__availability__day_of_week=day_of_week,
                pandit_profile__availability__is_available=True
            ).distinct()
        
        # Filter by availability (specific_date)
        if specific_date:
            from django.utils.dateparse import parse_date
            from datetime import datetime
            parsed_date = parse_date(specific_date)
            if parsed_date:
                # Get day of week for the specific date
                day_of_week_for_date = parsed_date.weekday()  # Monday=0, Sunday=6
                from availability.models import Availability
                queryset = queryset.filter(
                    pandit_profile__availability__day_of_week=day_of_week_for_date,
                    pandit_profile__availability__is_available=True
                ).distinct()
        
        # Filter by time range (if provided)
        if start_time or end_time:
            from django.utils.dateparse import parse_time
            from availability.models import Availability
            
            availability_filter = Q()
            if start_time:
                parsed_start = parse_time(start_time)
                if parsed_start:
                    availability_filter |= Q(
                        pandit_profile__availability__start_time__lte=parsed_start
                    )
            if end_time:
                parsed_end = parse_time(end_time)
                if parsed_end:
                    availability_filter |= Q(
                        pandit_profile__availability__end_time__gte=parsed_end
                    )
            
            if availability_filter:
                queryset = queryset.filter(availability_filter).distinct()
        
        # Filter by call availability
        if enable_call is not None:
            if enable_call:
                # Filter for Pandits who have enable_call=True OR allow_call=True (backward compatibility)
                queryset = queryset.filter(
                    Q(pandit_profile__enable_call=True) | Q(pandit_profile__allow_call=True)
                ).distinct()
            else:
                # Filter for Pandits who have enable_call=False AND allow_call=False
                queryset = queryset.filter(
                    pandit_profile__enable_call=False,
                    pandit_profile__allow_call=False
                ).distinct()
        
        # Filter by WhatsApp availability
        if enable_whatsapp is not None:
            if enable_whatsapp:
                # Filter for Pandits who have enable_whatsapp=True OR allow_whatsapp=True (backward compatibility)
                queryset = queryset.filter(
                    Q(pandit_profile__enable_whatsapp=True) | Q(pandit_profile__allow_whatsapp=True)
                ).distinct()
            else:
                # Filter for Pandits who have enable_whatsapp=False AND allow_whatsapp=False
                queryset = queryset.filter(
                    pandit_profile__enable_whatsapp=False,
                    pandit_profile__allow_whatsapp=False
                ).distinct()
        
        # Exclude fully blocked Pandits (if requested)
        if exclude_fully_blocked:
            # This would check if Pandit has any availability
            # For now, we'll just return all active Pandits
            # Module 12 (Security) will handle blocking logic
            pass
        
        # Order by relevance (can be enhanced later)
        # For now, order by user creation date (newest first)
        queryset = queryset.order_by('-created_at')
        
        return queryset


class PageSearchService:
    """
    Service for Page/Temple search operations.
    
    All methods are read-only.
    No mutations, no side effects, no business logic.
    Isolated from Pandit search.
    """
    
    @staticmethod
    def search_pages(
        city_id: Optional[int] = None,
        area_id: Optional[int] = None,
        page_type: Optional[str] = None,
        keyword: Optional[str] = None,
        has_announcements: Optional[bool] = None,
        has_events: Optional[bool] = None,
        recently_updated: Optional[bool] = None
    ):
        """
        Search for Pages based on criteria.
        
        Args:
            city_id: Filter by city
            area_id: Filter by area
            page_type: Filter by page type (TEMPLE, BRAND, etc.)
            keyword: Search in title and description
            has_announcements: Filter pages with announcements
            has_events: Filter pages with upcoming events
            recently_updated: Filter recently updated pages
        
        Returns:
            QuerySet of Page objects with status=ACTIVE and is_deleted=False
        
        Note:
            - Only returns ACTIVE pages
            - INVISIBLE pages are excluded from search (but accessible via direct URL)
            - Read-only query, no mutations
        """
        from pages.models import Page
        from pages.constants import PAGE_STATUS_ACTIVE, PAGE_STATUS_INVISIBLE, PAGE_STATUS_DEACTIVATED
        
        # TASK 19: Base queryset: Active pages only, not deleted (visibility enforced at query time)
        # Database is authoritative - never show invisible/deactivated pages
        # Index is derived, not truth - filtering always applied before returning results
        queryset = Page.objects.filter(
            status=PAGE_STATUS_ACTIVE,  # TASK 19: Only ACTIVE status
            is_deleted=False,            # TASK 19: Never show deleted pages
            # TASK 19: Exclude INVISIBLE pages from search (but accessible via direct URL)
        ).exclude(
            status=PAGE_STATUS_INVISIBLE  # TASK 19: Exclude invisible pages from search
        ).exclude(
            status=PAGE_STATUS_DEACTIVATED  # TASK 19: Exclude deactivated pages from search
        ).select_related('city', 'area', 'created_by')
        
        # Filter by page_type
        if page_type:
            queryset = queryset.filter(page_type=page_type)
        
        # Filter by city
        if city_id:
            queryset = queryset.filter(city_id=city_id)
        
        # Filter by area
        if area_id:
            queryset = queryset.filter(area_id=area_id)
        
        # Filter by keyword (search in title and description)
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(address__icontains=keyword)
            )
        
        # Filter by has_announcements (pages with posts of type ANNOUNCEMENT)
        if has_announcements:
            from pages.models import PagePost
            pages_with_announcements = PagePost.objects.filter(
                post_type='ANNOUNCEMENT',
                is_deleted=False,
                is_hidden=False
            ).values_list('page_id', flat=True).distinct()
            queryset = queryset.filter(id__in=pages_with_announcements)
        
        # Filter by has_events (pages with posts of type EVENT)
        if has_events:
            from pages.models import PagePost
            from django.utils import timezone
            pages_with_events = PagePost.objects.filter(
                post_type='EVENT',
                is_deleted=False,
                is_hidden=False,
                event_date__gte=timezone.now().date()
            ).values_list('page_id', flat=True).distinct()
            queryset = queryset.filter(id__in=pages_with_events)
        
        # Filter by recently_updated (updated in last 30 days)
        if recently_updated:
            from django.utils import timezone
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(updated_at__gte=thirty_days_ago)
        
        # Order by creation date (newest first)
        queryset = queryset.order_by('-created_at')
        
        return queryset
