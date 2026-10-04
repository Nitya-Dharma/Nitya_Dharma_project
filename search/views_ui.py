"""
Search UI views (template-based).
These views render HTML templates for search functionality.
"""
from django.conf import settings
from django.shortcuts import render
from masterdata.models import City, LocalArea, Pooja, PoojaCategory
from services.location_utils import validate_coordinates
from .services import SearchService, PageSearchService



def _resolve_search_ui_mode(request, result_type):
    """
    Slice-1 Search UI mode for four-tab chrome.

    Precedence (Step 15):
    1. type=bureau
    2. tab=experts or legacy expert tab values
    3. result_type=pages
    4. pandits (default)

    Does not alter SearchService / PageSearchService semantics when mode is
    pandits or pages. Bureau mode is handled separately in search_results.
    """
    type_param = (request.GET.get("type") or "").strip().lower()
    if type_param == "bureau":
        return "bureau"

    tab = (request.GET.get("tab") or "").strip().lower()
    if tab == "experts" or tab in ("astrology", "numerology", "palmistry"):
        return "experts"

    if result_type == "pages":
        return "pages"
    return "pandits"


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
    
    # Slice-1/2 mode chrome
    search_ui_mode = _resolve_search_ui_mode(request, result_type)

    # Resolve Expert subtype before any Expert query (canonical + legacy tab=).
    ALLOWED_EXPERT_TYPES = ("astrology", "numerology", "palmistry")
    expert_type = (request.GET.get("expert_type") or "").strip().lower()
    if search_ui_mode == "experts":
        if expert_type not in ALLOWED_EXPERT_TYPES:
            expert_type = ""
        if not expert_type:
            legacy_tab = (request.GET.get("tab") or "").strip().lower()
            if legacy_tab in ALLOWED_EXPERT_TYPES:
                expert_type = legacy_tab

    # Perform search (backend logic) - BRANCH ON mode / result_type
    # Production Pandit/Page semantics unchanged when those modes are active.
    search_results_list = []
    pagination = None
    is_page_search = result_type == 'pages'

    experts = []
    expert_page_obj = None
    experts_pagination = None
    expert_result_count = None

    bureaus = []
    bureau_page_obj = None
    bureaus_pagination = None
    bureau_result_count = None
    bureau_city_filter = ""
    bureau_caste_filter = ""
    bureau_caste_groups = ()
    bureau_is_capped = False

    if search_ui_mode == "bureau":
        # Bureau-only query via canonical public visibility helper.
        try:
            from django.core.paginator import Paginator, EmptyPage
            from django.db.models import Q
            from bureaus.utils import get_visible_bureaus
            from bureaus.views import (
                ALLOWED_CASTES,
                CASTE_GROUPS,
                _bureau_has_caste,
                _is_valid_caste_data_structure,
            )

            BUREAU_SEARCH_PAGE_SIZE = 12
            list_only_fields = (
                "id",
                "public_id",
                "bureau_name",
                "city",
                "profile_image",
                "description",
            )

            # Bureau city is free-text (existing /bureaus/ list semantics), not masterdata id.
            bureau_city_filter = (request.GET.get("city") or "").strip()
            caste = (request.GET.get("caste") or "").strip().lower()
            bureau_caste_groups = CASTE_GROUPS

            bureaus_qs = (
                get_visible_bureaus()
                .only(*list_only_fields)
                .order_by("-created_at", "-id")
            )

            if bureau_city_filter:
                bureaus_qs = bureaus_qs.filter(city=bureau_city_filter)

            q = request.GET.get("q")
            if not q:
                q = keyword
            if q:
                bureaus_qs = bureaus_qs.filter(
                    Q(bureau_name__icontains=q)
                    | Q(description__icontains=q)
                    | Q(city__icontains=q)
                )

            bureaus_data = bureaus_qs
            if caste and caste not in ALLOWED_CASTES:
                bureaus_data = []
            elif caste:
                bureaus_qs = bureaus_qs.only(*list_only_fields, "caste_data")
                caste_filter_soft_cap = 500
                ordered_bureaus = list(bureaus_qs.iterator(chunk_size=100))
                filtered_bureaus = []
                for bureau in ordered_bureaus:
                    if _is_valid_caste_data_structure(
                        bureau.caste_data
                    ) and _bureau_has_caste(bureau, caste):
                        filtered_bureaus.append(bureau)
                if len(filtered_bureaus) > caste_filter_soft_cap:
                    bureau_is_capped = True
                    filtered_bureaus = filtered_bureaus[:caste_filter_soft_cap]
                bureaus_data = filtered_bureaus
                bureau_caste_filter = caste

            if isinstance(bureaus_data, list):
                bureau_result_count = len(bureaus_data)
            else:
                bureau_result_count = bureaus_data.count()

            paginator = Paginator(bureaus_data, BUREAU_SEARCH_PAGE_SIZE)
            page = int(request.GET.get("page", 1))
            try:
                bureau_page_obj = paginator.page(page)
            except EmptyPage:
                bureau_page_obj = paginator.page(paginator.num_pages)
            bureaus_pagination = {
                "page": page,
                "current_page": page,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": bureau_page_obj.has_next(),
                "has_previous": bureau_page_obj.has_previous(),
                "next_page_number": bureau_page_obj.next_page_number()
                if bureau_page_obj.has_next()
                else None,
                "previous_page_number": bureau_page_obj.previous_page_number()
                if bureau_page_obj.has_previous()
                else None,
            }
            bureaus = bureau_page_obj
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "Bureau search section failed", exc_info=True
            )
            bureaus = []
            bureau_page_obj = None
            bureaus_pagination = None
            bureau_result_count = 0
            bureau_city_filter = ""
            bureau_caste_filter = ""
            bureau_caste_groups = ()
            bureau_is_capped = False
    elif search_ui_mode == "experts":
        # Expert-only query. Invalid/missing expert_type => empty (no arbitrary default).
        if expert_type in ALLOWED_EXPERT_TYPES:
            try:
                from django.core.paginator import Paginator, EmptyPage
                from django.db.models import Avg, Prefetch
                from core.api_constants import DEFAULT_SEARCH_PAGE_SIZE
                from core.models import ExpertProfile, ExpertService
                from services.expert_discovery import filter_experts_offering

                experts_queryset = ExpertProfile.objects.filter(
                    is_active=True
                ).prefetch_related(
                    Prefetch(
                        "services",
                        queryset=ExpertService.objects.filter(is_active=True),
                        to_attr="active_services",
                    )
                )
                try:
                    experts_queryset = filter_experts_offering(
                        experts_queryset,
                        expert_type,
                    )
                except ValueError:
                    experts_queryset = ExpertProfile.objects.none()

                q = request.GET.get("q")
                if not q:
                    q = keyword
                if q:
                    experts_queryset = experts_queryset.filter(name__icontains=q)

                min_exp_raw = request.GET.get("min_exp")
                if min_exp_raw:
                    try:
                        min_exp_int = int(min_exp_raw)
                        if min_exp_int >= 0:
                            experts_queryset = experts_queryset.filter(
                                experience_years__gte=min_exp_int
                            )
                    except (TypeError, ValueError):
                        pass

                min_rating_raw = request.GET.get("min_rating")
                if min_rating_raw:
                    try:
                        min_rating_val = float(min_rating_raw)
                        if min_rating_val > 0:
                            experts_queryset = experts_queryset.filter(
                                rating__gte=min_rating_val
                            )
                    except (TypeError, ValueError):
                        pass

                if (request.GET.get("verified") or "").strip() == "1":
                    experts_queryset = experts_queryset.filter(is_verified=True)

                experts_queryset = experts_queryset.annotate(
                    avg_rating=Avg("reviews__rating")
                )
                experts_queryset = experts_queryset.order_by(
                    "-experience_years", "-avg_rating"
                )

                expert_result_count = experts_queryset.count()
                paginator = Paginator(experts_queryset, DEFAULT_SEARCH_PAGE_SIZE)
                page = int(request.GET.get("page", 1))
                try:
                    expert_page_obj = paginator.page(page)
                except EmptyPage:
                    expert_page_obj = paginator.page(paginator.num_pages)
                experts_pagination = {
                    "page": page,
                    "current_page": page,
                    "total_pages": paginator.num_pages,
                    "total_count": paginator.count,
                    "has_next": expert_page_obj.has_next(),
                    "has_previous": expert_page_obj.has_previous(),
                    "next_page_number": expert_page_obj.next_page_number()
                    if expert_page_obj.has_next()
                    else None,
                    "previous_page_number": expert_page_obj.previous_page_number()
                    if expert_page_obj.has_previous()
                    else None,
                }
                experts = expert_page_obj
            except Exception:
                import logging

                logging.getLogger(__name__).warning(
                    "Expert search section failed", exc_info=True
                )
                experts = []
                expert_page_obj = None
                experts_pagination = None
                expert_result_count = 0
        else:
            experts = []
            expert_result_count = 0
    # Explicit branching: Pandits OR Pages (never mixed)
    elif is_page_search:
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

    display_results = search_results_list
    display_count = pagination["total_count"] if pagination else 0
    display_pagination = pagination
    # Expert/Bureau modes must not inherit Pandit/Page result lists or pagination.
    if search_ui_mode in ("experts", "bureau"):
        display_results = []
        display_count = None
        display_pagination = None

    # Prepare context for template
    context = {
        "search_results": display_results,
        "result_count": display_count,
        "pagination": display_pagination,
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
        'search_ui_mode': search_ui_mode,
        'expert_type': expert_type if search_ui_mode == 'experts' else None,
        'experts': experts if search_ui_mode == 'experts' else [],
        'expert_page_obj': expert_page_obj if search_ui_mode == 'experts' else None,
        'expert_result_count': expert_result_count if search_ui_mode == 'experts' else None,
        'experts_pagination': experts_pagination if search_ui_mode == 'experts' else None,
        'bureaus': bureaus if search_ui_mode == 'bureau' else [],
        'bureau_page_obj': bureau_page_obj if search_ui_mode == 'bureau' else None,
        'bureau_result_count': bureau_result_count if search_ui_mode == 'bureau' else None,
        'bureaus_pagination': bureaus_pagination if search_ui_mode == 'bureau' else None,
        'bureau_city_filter': bureau_city_filter if search_ui_mode == 'bureau' else '',
        'bureau_caste_filter': bureau_caste_filter if search_ui_mode == 'bureau' else '',
        'bureau_caste_groups': bureau_caste_groups if search_ui_mode == 'bureau' else (),
        'bureau_is_capped': bureau_is_capped if search_ui_mode == 'bureau' else False,
        'search_mode_deferred': False,
    }

    return render(request, 'module7_search/search_results.html', context)

