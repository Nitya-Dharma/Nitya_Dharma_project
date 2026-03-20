"""
Search API views.

Tasks:
- 7.14: Search API (Read-Only)
- 7.15: Search Safety, Validation & Rate Limit Hooks
Phase 10C: Search result caching (5 min TTL, cache hit/miss logging).
"""

import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage
from django.core.cache import cache
from core.api_constants import MAX_PAGE_SIZE, DEFAULT_SEARCH_PAGE_SIZE
from core.public_id import resolve_public_id, reject_bigint_id
from .serializers import PanditSearchResultSerializer
from .services import SearchService, SearchAnalyticsService, SearchClickTrackingService, RecommendationService, SEARCH_CACHE_TIMEOUT
from .logging import log_search_request
from profiles.models import PanditProfile

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def search_pandits(request):
    """
    Search Pandits endpoint.
    
    Task 7.14: Search API (Read-Only)
    Task 7.15: Search Safety, Validation & Rate Limit Hooks
    
    GET /api/search/pandits/
    
    Query Parameters:
        - q (or query): Optional text search (name/bio); uses FULLTEXT on MySQL, icontains fallback
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

    # STEP-3: Location-based search when lat/lon provided (extends search, does not replace)
    lat = request.GET.get("lat")
    lon = request.GET.get("lon")
    if lat is not None and lon is not None and str(lat).strip() != "" and str(lon).strip() != "":
        try:
            from search.location_search_service import find_nearby_pandits
            radius_km = 20
            if request.GET.get("radius_km"):
                try:
                    r = float(request.GET.get("radius_km"))
                    if 0 < r <= 500:
                        radius_km = r
                except (ValueError, TypeError):
                    pass
            results = find_nearby_pandits(lat, lon, radius_km=radius_km)
            return JsonResponse({"status": "success", "results": results})
        except ValueError:
            return JsonResponse(
                {"status": "error", "message": "Invalid location coordinates"},
                status=400,
            )

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
    
    # Phase 10B: Optional text search (FULLTEXT on MySQL, icontains fallback)
    if 'q' in query_params and query_params['q']:
        validated_data['query'] = query_params['q'].strip()
    elif 'query' in query_params and query_params['query']:
        validated_data['query'] = query_params['query'].strip()

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

    # Phase 10C: Only cache meaningful searches (Steps 5–6)
    cacheable = SearchService.is_search_cacheable(validated_data.get('query'))
    cache_key = None
    if cacheable:
        cache_key = SearchService.build_search_cache_key(
            query=validated_data.get('query'),
            page=page,
            page_size=page_size,
            city_id=validated_data.get('city_id'),
            area_id=validated_data.get('area_id'),
            pooja_id=validated_data.get('pooja_id'),
            day_of_week=validated_data.get('day_of_week'),
            specific_date=validated_data.get('specific_date'),
            start_time=validated_data.get('start_time'),
            end_time=validated_data.get('end_time'),
            enable_call=validated_data.get('enable_call'),
            enable_whatsapp=validated_data.get('enable_whatsapp'),
        )
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug("search cache hit for key=%s", cache_key)
            return JsonResponse(cached_result)
        logger.debug("search cache miss for key=%s", cache_key)
    
    try:
        # Phase 10E: Track search query for trending (only valid queries)
        if validated_data.get("query"):
            SearchAnalyticsService.track_search_query(validated_data.get("query"))
        # Phase 14: Behavior analytics (passive; does not change results)
        try:
            from behavior_engine.trackers import track_search_query
            track_search_query(request, validated_data.get("query"), metadata={
                "query": (validated_data.get("query") or "")[:200],
                "city": validated_data.get("city_id"),
            })
        except Exception:
            pass

        # Phase 10F: Session-based related search tracking (previous → current)
        current_sanitized = (
            SearchService._sanitize_search_query(validated_data.get("query"))
            if validated_data.get("query")
            else ""
        )
        if current_sanitized and len(current_sanitized) >= 3:
            previous_query = request.session.get("last_search_query")
            SearchAnalyticsService.track_related_search(previous_query, current_sanitized)
            request.session["last_search_query"] = current_sanitized

        # Perform search (Phase 10B: optional query for FULLTEXT/icontains)
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
            enable_whatsapp=validated_data.get('enable_whatsapp'),
            query=validated_data.get('query'),
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
        
        response_data = {
            'results': results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }
        # Phase 10E: Empty search result suggestions
        if len(results) == 0:
            response_data['suggested_searches'] = SearchAnalyticsService.get_trending_searches()
        # Phase 10F: Related searches when a query was used
        if validated_data.get("query"):
            response_data["related_searches"] = SearchAnalyticsService.get_related_searches(
                validated_data.get("query")
            )

        # Phase 10C: Cache result (Step 4) — 5 minutes
        if cacheable and cache_key:
            cache.set(cache_key, response_data, timeout=SEARCH_CACHE_TIMEOUT)
        
        return JsonResponse(response_data)
    
    except Exception as e:
        # Log error but don't expose internal details
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': 'An error occurred while performing search'},
            status=500
        )


@require_http_methods(["GET"])
def search_suggestions(request):
    """
    Phase 10D: Autocomplete suggestions for search.
    GET /api/search/suggestions/?q=pu
    Returns {"suggestions": ["puja", "puja pandit", ...]}.
    No auth required; query length and count limited to prevent abuse.
    """
    q = (request.GET.get("q") or "").strip()
    suggestions = SearchService.get_search_suggestions(q)
    return JsonResponse({"suggestions": suggestions})


@require_http_methods(["GET"])
def trending_searches(request):
    """
    Phase 10E: Trending search queries for homepage and empty-result suggestions.
    GET /api/search/trending/
    Returns {"trending": ["puja pandit hyderabad", "temple puja", ...]}.
    Cached 10 minutes.
    """
    trending = SearchAnalyticsService.get_trending_searches()
    return JsonResponse({"trending": trending})


@require_http_methods(["GET"])
def related_searches(request):
    """
    Phase 10F: Related searches ("People also searched for") for a given query.
    GET /api/search/related/?q=puja hyderabad
    Returns {"related": ["temple puja", "griha pravesh puja", ...]}.
    Cached 10 minutes.
    """
    q = (request.GET.get("q") or "").strip()
    related = SearchAnalyticsService.get_related_searches(q)
    return JsonResponse({"related": related})


@require_http_methods(["POST"])
def search_result_click(request):
    """
    Phase 11C1: Track which pandit profile was clicked from search results.
    POST /api/search/click/
    Body: {"query": "puja hyderabad", "pandit_id": "<public_id>"}
    Returns: {"status": "ok"}
    Abuse protection: query length >= 3, valid pandit, no duplicate same session within 5s.
    """
    import json
    from core.security_utils import safe_json_loads
    from django.core.exceptions import ValidationError

    try:
        allowed_fields = ["query", "pandit_id"]
        data = safe_json_loads(request.body, allowed_fields=allowed_fields)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except ValidationError as e:
        return JsonResponse({"error": "Invalid payload", "message": str(e)}, status=400)

    pandit_public_id = data.get("pandit_id")
    if not pandit_public_id:
        return JsonResponse({"error": "pandit_id is required"}, status=400)
    pandit_public_id = str(pandit_public_id).strip()
    if reject_bigint_id(pandit_public_id):
        return JsonResponse({"error": "Invalid pandit identifier"}, status=400)

    pandit_profile = resolve_public_id(PanditProfile, pandit_public_id)
    if not pandit_profile:
        return JsonResponse({"error": "Pandit not found"}, status=404)

    session_id = (request.session.session_key or "").strip()
    if not session_id and request.session:
        request.session.save()
        session_id = request.session.session_key or ""

    SearchClickTrackingService.track_click(
        query=data.get("query"),
        pandit_profile=pandit_profile,
        user=request.user,
        session_id=session_id,
    )
    # Phase 14: Behavior analytics (passive)
    try:
        from behavior_engine.trackers import track_search_click
        track_search_click(request, pandit_profile.id, metadata={})
    except Exception:
        pass
    return JsonResponse({"status": "ok"})


RECOMMENDATIONS_CACHE_KEY = "recommendations:pandits"
RECOMMENDATIONS_CACHE_TIMEOUT = 300


@require_http_methods(["GET"])
def recommended_pandits(request):
    """
    Phase 11F: Recommended Pandits for homepage, empty-state, and similar pandits.
    GET /api/recommendations/pandits/
    Returns {"recommended": [{"public_id": "...", "name": "..."}, ...]}.
    Cached 5 minutes.
    """
    cached = cache.get(RECOMMENDATIONS_CACHE_KEY)
    if cached is not None:
        return JsonResponse(cached)
    profiles = RecommendationService.get_recommended_pandits(limit=10)
    payload = {
        "recommended": [
            {"public_id": (p.public_id or ""), "name": (p.get_display_name() or "")}
            for p in profiles
        ],
    }
    cache.set(RECOMMENDATIONS_CACHE_KEY, payload, RECOMMENDATIONS_CACHE_TIMEOUT)
    logger.debug("recommendations generated count=%s", len(profiles))
    return JsonResponse(payload)
