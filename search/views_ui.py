"""
Search UI views (template-based).
These views render HTML templates for search functionality.
"""
from django.conf import settings
from django.shortcuts import render
from masterdata.models import City, LocalArea, Pooja, PoojaCategory
from services.location_utils import validate_coordinates
from .services import SearchService, PageSearchService


def search_results(request):
    """
    Search results page (HTML template).
    
    Renders search results in HTML format.
    Backend performs search, UI only displays.
    """
    # Get search parameters from query string
    result_type = request.GET.get('result_type', 'pandits')  # Default to pandits
    city_id = request.GET.get('city')
    area_id = request.GET.get('area')
    pooja_id = request.GET.get('pooja')
    keyword = request.GET.get('keyword', '').strip()
    available_date = request.GET.get('available_date')
    page_type = request.GET.get('page_type')  # For page filtering
    has_announcements = request.GET.get('has_announcements') == '1'
    has_events = request.GET.get('has_events') == '1'
    recently_updated = request.GET.get('recently_updated') == '1'
    
    # Convert to integers if provided
    try:
        city_id = int(city_id) if city_id else None
    except (ValueError, TypeError):
        city_id = None
    
    try:
        area_id = int(area_id) if area_id else None
    except (ValueError, TypeError):
        area_id = None
    
    try:
        pooja_id = int(pooja_id) if pooja_id else None
    except (ValueError, TypeError):
        pooja_id = None
    
    # Master data for filters (hierarchy: Pooja Category → Pooja)
    cities = City.objects.filter(is_active=True).order_by('name')
    areas = LocalArea.objects.filter(is_active=True).select_related('city').order_by('city__name', 'name')
    pooja_categories = PoojaCategory.objects.filter(is_active=True).order_by('display_order', 'name')
    poojas = Pooja.objects.filter(is_active=True).select_related('pooja_category').order_by(
        'pooja_category__display_order', 'pooja_category__name', 'name'
    )
    
    # Perform search (backend logic) - BRANCH ON result_type
    search_results_list = []
    pagination = None
    is_page_search = result_type == 'pages'
    
    # Explicit branching: Pandits OR Pages (never mixed)
    if is_page_search:
        # PAGE SEARCH - Isolated from Pandit search
        try:
            queryset = PageSearchService.search_pages(
                city_id=city_id,
                area_id=area_id,
                page_type=page_type,
                keyword=keyword,
                has_announcements=has_announcements,
                has_events=has_events,
                recently_updated=recently_updated
            )
            
            # Pagination
            from django.core.paginator import Paginator, EmptyPage
            from core.api_constants import DEFAULT_SEARCH_PAGE_SIZE
            paginator = Paginator(queryset, DEFAULT_SEARCH_PAGE_SIZE)
            page = int(request.GET.get('page', 1))
            try:
                page_obj = paginator.page(page)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
            
            search_results_list = list(page_obj)
            pagination = {
                'page': page,
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
                'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
            }
        except Exception as e:
            # Log error but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Page search error: {str(e)}", exc_info=True)
            search_results_list = []
    
    else:
        # PANDIT SEARCH - Isolated from Page search
        if city_id or area_id or pooja_id or keyword:
            try:
                queryset = SearchService.search_pandits(
                    city_id=city_id,
                    area_id=area_id,
                    pooja_id=pooja_id,
                    exclude_fully_blocked=True
                )
                
                # Filter by keyword if provided (simple name/email search)
                if keyword:
                    from django.db.models import Q
                    queryset = queryset.filter(
                        Q(email__icontains=keyword) |
                        Q(pandit_profile__display_name__icontains=keyword) |
                        Q(pandit_profile__about_description__icontains=keyword)
                    ).distinct()
                
                # Pagination (PART 3 hardening: use constant)
                from django.core.paginator import Paginator, EmptyPage
                from core.api_constants import DEFAULT_SEARCH_PAGE_SIZE
                paginator = Paginator(queryset, DEFAULT_SEARCH_PAGE_SIZE)
                page = int(request.GET.get('page', 1))
                try:
                    page_obj = paginator.page(page)
                except EmptyPage:
                    page_obj = paginator.page(paginator.num_pages)
                
                # Convert User objects to PanditProfile objects for template
                from profiles.models import PanditProfile
                pandit_profiles = []
                for user in page_obj:
                    try:
                        profile = user.pandit_profile
                        pandit_profiles.append(profile)
                    except PanditProfile.DoesNotExist:
                        # Skip users without profiles
                        continue
                
                search_results_list = pandit_profiles
                pagination = {
                    'page': page,
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                    'next_page_number': page_obj.next_page_number() if page_obj.has_next() else None,
                    'previous_page_number': page_obj.previous_page_number() if page_obj.has_previous() else None,
                }
            except Exception as e:
                # Log error but don't crash
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Pandit search error: {str(e)}", exc_info=True)
                search_results_list = []
    
    # Prepare selected_filters for display (with proper values)
    selected_filters = {}
    if city_id:
        city_obj = cities.filter(id=city_id).first()
        if city_obj:
            selected_filters['city'] = city_obj.name
    if area_id:
        area_obj = areas.filter(id=area_id).first()
        if area_obj:
            selected_filters['area'] = f"{area_obj.name}, {area_obj.city.name}"
    selected_pooja = None
    if pooja_id:
        pooja_obj = poojas.filter(id=pooja_id).first()
        if pooja_obj:
            selected_filters['pooja'] = pooja_obj.name
            selected_pooja = pooja_obj
    if keyword:
        selected_filters['keyword'] = keyword
    if available_date:
        selected_filters['available_date'] = available_date
    
    # Effective location for "Pandits near you": lat/lon from GET or debug_lat/debug_lon when DEBUG
    location_lat = request.GET.get("lat")
    location_lon = request.GET.get("lon")
    debug_lat_raw = request.GET.get("debug_lat")
    debug_lon_raw = request.GET.get("debug_lon")
    debug_location = False
    client_ip = request.META.get("REMOTE_ADDR") or ""
    if (
        settings.DEBUG
        and client_ip in ("127.0.0.1", "::1")
        and debug_lat_raw is not None
        and debug_lon_raw is not None
    ):
        try:
            lat_val, lon_val = validate_coordinates(debug_lat_raw, debug_lon_raw)
            location_lat = lat_val
            location_lon = lon_val
            debug_location = True
        except ValueError:
            debug_lat_raw = None
            debug_lon_raw = None
            # Leave location_lat/location_lon as from request (lat/lon); invalid debug coords ignored

    # Prepare context for template
    context = {
        'search_results': search_results_list,
        'result_count': pagination['total_count'] if pagination else 0,
        'pagination': pagination,
        'cities': cities,
        'areas': areas,
        'pooja_categories': pooja_categories,
        'poojas': poojas,
        'selected_pooja': selected_pooja,
        'selected_filters': selected_filters,
        'current_filters': {
            'city_id': city_id,
            'area_id': area_id,
            'pooja_id': pooja_id,
            'keyword': keyword,
            'available_date': available_date,
        },
        'has_results': len(search_results_list) > 0,
        'has_filters': bool(city_id or area_id or pooja_id or keyword or page_type),
        'sort_options': [],  # Backend can provide sort options later
        'current_sort': None,  # Backend can provide current sort
        'result_type': result_type,  # Pass to template for conditional rendering
        'page_type': page_type,  # Pass page_type to template
        'location_lat': location_lat,
        'location_lon': location_lon,
        'debug_location': debug_location,
        'debug_lat': debug_lat_raw,
        'debug_lon': debug_lon_raw,
    }

    return render(request, 'module7_search/search_results.html', context)

