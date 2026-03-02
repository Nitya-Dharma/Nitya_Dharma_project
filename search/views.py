"""
Search API views.

Tasks:
- 7.14: Search API (Read-Only)
- 7.15: Search Safety, Validation & Rate Limit Hooks

Read-only GET endpoints for search functionality.
No mutations, no side effects.
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage
from core.api_constants import MAX_PAGE_SIZE, DEFAULT_SEARCH_PAGE_SIZE
from .serializers import PanditSearchResultSerializer
from .services import SearchService
from .logging import log_search_request

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def search_pandits(request):
    """
    Search Pandits endpoint.
    
    Task 7.14: Search API (Read-Only)
    Task 7.15: Search Safety, Validation & Rate Limit Hooks
    
    GET /api/search/pandits/
    
    Query Parameters:
        - city_id: Optional City ID
        - area_id: Optional LocalArea ID
        - pooja_id: Optional Pooja ID
        - day_of_week: Optional day of week (0-6, Monday-Sunday)
        - specific_date: Optional specific date (YYYY-MM-DD)
        - start_time: Optional start time (HH:MM:SS)
        - end_time: Optional end time (HH:MM:SS)
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20, max: 100)
    
    Returns:
        Paginated list of Pandit search results
    
    Note:
        - Read-only endpoint (GET only)
        - No mutations
        - No side effects
        - Input validation applied
        - Rate limit hooks (delegated to Module 12)
    """
    # Task 7.15: Input sanitization and validation
    # Parse query parameters
    query_params = request.GET.dict()
    
    # Convert string values to appropriate types
    validated_data = {}
    if 'city_id' in query_params and query_params['city_id']:
        try:
            validated_data['city_id'] = int(query_params['city_id'])
        except (ValueError, TypeError):
            return JsonResponse(
                {'error': 'Invalid city_id'},
                status=400
            )
    
    if 'area_id' in query_params and query_params['area_id']:
        try:
            validated_data['area_id'] = int(query_params['area_id'])
        except (ValueError, TypeError):
            return JsonResponse(
                {'error': 'Invalid area_id'},
                status=400
            )
    
    if 'pooja_id' in query_params and query_params['pooja_id']:
        try:
            validated_data['pooja_id'] = int(query_params['pooja_id'])
        except (ValueError, TypeError):
            return JsonResponse(
                {'error': 'Invalid pooja_id'},
                status=400
            )
    
    if 'day_of_week' in query_params and query_params['day_of_week']:
        try:
            day_of_week = int(query_params['day_of_week'])
            if day_of_week < 0 or day_of_week > 6:
                return JsonResponse(
                    {'error': 'day_of_week must be between 0 and 6'},
                    status=400
                )
            validated_data['day_of_week'] = day_of_week
        except (ValueError, TypeError):
            return JsonResponse(
                {'error': 'Invalid day_of_week'},
                status=400
            )
    
    if 'specific_date' in query_params and query_params['specific_date']:
        from django.utils.dateparse import parse_date
        specific_date = parse_date(query_params['specific_date'])
        if specific_date is None:
            return JsonResponse(
                {'error': 'Invalid specific_date format. Use YYYY-MM-DD'},
                status=400
            )
        validated_data['specific_date'] = specific_date
    
    if 'start_time' in query_params and query_params['start_time']:
        from django.utils.dateparse import parse_time
        start_time = parse_time(query_params['start_time'])
        if start_time is None:
            return JsonResponse(
                {'error': 'Invalid start_time format. Use HH:MM:SS'},
                status=400
            )
        validated_data['start_time'] = start_time
    
    if 'end_time' in query_params and query_params['end_time']:
        from django.utils.dateparse import parse_time
        end_time = parse_time(query_params['end_time'])
        if end_time is None:
            return JsonResponse(
                {'error': 'Invalid end_time format. Use HH:MM:SS'},
                status=400
            )
        validated_data['end_time'] = end_time
    
    # Filter by call availability
    if 'enable_call' in query_params and query_params['enable_call']:
        enable_call_str = query_params['enable_call'].lower()
        if enable_call_str in ('true', '1', 'yes'):
            validated_data['enable_call'] = True
        elif enable_call_str in ('false', '0', 'no'):
            validated_data['enable_call'] = False
    
    # Filter by WhatsApp availability
    if 'enable_whatsapp' in query_params and query_params['enable_whatsapp']:
        enable_whatsapp_str = query_params['enable_whatsapp'].lower()
        if enable_whatsapp_str in ('true', '1', 'yes'):
            validated_data['enable_whatsapp'] = True
        elif enable_whatsapp_str in ('false', '0', 'no'):
            validated_data['enable_whatsapp'] = False
    
    # Pagination parameters
    try:
        page = int(query_params.get('page', 1))
        page_size = int(query_params.get('page_size', DEFAULT_SEARCH_PAGE_SIZE))
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = DEFAULT_SEARCH_PAGE_SIZE
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE
    except (ValueError, TypeError):
        page = 1
        page_size = DEFAULT_SEARCH_PAGE_SIZE
    
    # Additional validation using service layer
    is_valid, error_message = SearchService.validate_search_params(
        city_id=validated_data.get('city_id'),
        area_id=validated_data.get('area_id'),
        pooja_id=validated_data.get('pooja_id'),
        day_of_week=validated_data.get('day_of_week'),
        specific_date=validated_data.get('specific_date')
    )
    
    if not is_valid:
        return JsonResponse(
            {'error': error_message},
            status=400
        )
    
    # Task 7.15: Rate limit hooks (delegated to Module 12)
    # TODO: When Module 12 (Security) is implemented, add rate limiting here
    # For now, this is a placeholder hook
    
    try:
        # Perform search
        queryset = SearchService.search_pandits(
            city_id=validated_data.get('city_id'),
            area_id=validated_data.get('area_id'),
            pooja_id=validated_data.get('pooja_id'),
            day_of_week=validated_data.get('day_of_week'),
            specific_date=validated_data.get('specific_date'),
            start_time=validated_data.get('start_time'),
            end_time=validated_data.get('end_time'),
            exclude_fully_blocked=True,
            enable_call=validated_data.get('enable_call'),
            enable_whatsapp=validated_data.get('enable_whatsapp')
        )
        
        # Pagination
        paginator = Paginator(queryset, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Serialize results
        results = [PanditSearchResultSerializer.serialize(pandit) for pandit in page_obj]
        
        # Task 7.16: Log search request (no PII)
        log_search_request(
            request=request,
            filters=validated_data,
            result_count=len(results)
        )
        
        # Return paginated response
        return JsonResponse({
            'results': results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        })
    
    except Exception as e:
        # Log error but don't expose internal details
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while performing search'},
            status=500
        )
