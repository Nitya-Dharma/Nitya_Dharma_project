from django.shortcuts import render
from masterdata.models import City, LocalArea, Pooja
from masterdata.services import (
    get_active_cities,
    get_active_local_areas,
    get_active_poojas,
    get_active_pooja_categories,
)

def home(request):
    """
    Home page view with hero section and search.
    Backend provides master data for filters and navigation.
    """
    # Provide context for navbar
    context = {
        'user': request.user if request.user.is_authenticated else None,
        'user_role': None,
        'is_profile_owner': False,
    }
    
    if request.user.is_authenticated:
        # Determine user role for navbar
        if hasattr(request.user, 'role'):
            if request.user.role == 'pandit':
                context['user_role'] = 'pandit'
            elif request.user.role == 'admin_pandit':
                context['user_role'] = 'admin_pandit'
            elif request.user.role == 'super_admin':
                context['user_role'] = 'super_admin'
            else:
                context['user_role'] = 'user'
    
    # Master data for search filters and navbar
    # Use service functions (no hardcoding - all data from database)
    from masterdata.services import (
        get_active_cities,
        get_active_local_areas,
        get_active_poojas,
        get_active_pooja_categories,
    )
    context['cities'] = get_active_cities()
    context['areas'] = get_active_local_areas()
    context['poojas'] = get_active_poojas()
    context['pooja_categories'] = get_active_pooja_categories()
    
    # Organize poojas by categories for navbar dropdown
    # Categories from PDF: Daily & Common Household, House/Property & Vehicle, Life Samskaras, Festival & Temple, Homams, Yagnas
    # Organize by exact name matching for specific poojas, then keyword matching for others
    all_poojas = list(context['poojas'])
    
    # Exact English names for matching (case-insensitive)
    # Include variations and keywords for flexible matching
    daily_poojas = [
        'Ganapati Puja', 'Ganesh Puja', 'Ganapathi Puja',
        'Navagraha Puja', 'Navagraha',
        'Satyanarayana Vratam', 'Satyanarayan Vratam', 'Satyanarayana Puja',
        'Lakshmi Puja', 'Laxmi Puja',
        'Durga Puja',
        'Hanuman Puja',
        'Rudrabhishekam', 'Rudra Abhishekam', 'Rudra Puja'
    ]
    
    # Keywords for daily poojas (for flexible matching)
    daily_keywords_list = [
        'ganapati', 'ganesh', 'ganapathi',
        'navagraha',
        'satyanarayana', 'satyanarayan',
        'lakshmi', 'laxmi',
        'durga',
        'hanuman',
        'rudrabhishekam', 'rudra', 'abhishekam'
    ]
    house_poojas = [
        'Bhoomi Puja', 'Gruha Pravesam', 'Gruha Pravesh', 'Vastu Shanti Puja', 'Vehicle Puja'
    ]
    samskara_poojas = [
        'Namakarana', 'Annaprashanam', 'Upanayanam', 'Vivaha Puja', 'Saptapadi'
    ]
    festival_poojas = [
        'Vinayaka Chaturthi', 'Navaratri Puja', 'Diwali Puja'
    ]
    homam_poojas = [
        'Ganapathi Homam', 'Navagraha Homam', 'Mrityunjaya Homam', 'Durga Homam'
    ]
    yagna_poojas = [
        'Satyanarayana Yagna', 'Putrakameshti Yagna', 'Ashvamedha Yagna'
    ]
    
    # Category keywords for fallback matching (comprehensive list)
    daily_keywords = ['ganapati', 'ganesh', 'ganapathi', 'navagraha', 'satyanarayana', 'satyanarayan', 'lakshmi', 'laxmi', 'durga', 'hanuman', 'rudrabhishekam', 'rudra', 'abhishekam', 'vratam', 'vratham']
    house_keywords = ['house', 'property', 'vehicle', 'griha', 'pravesh', 'vastu', 'bhoomi']
    samskara_keywords = ['samskara', 'namkaran', 'vivah', 'marriage', 'wedding', 'mundan', 'upanayanam', 'annaprashan']
    festival_keywords = ['festival', 'temple', 'navratri', 'diwali', 'dussehra', 'vinayaka', 'chaturthi']
    homam_keywords = ['homam', 'homa', 'yagya']
    yagna_keywords = ['yagna', 'yajna', 'yagam']
    
    pooja_categories = {
        'Daily & Common Household Poojas': [],
        'House, Property & Vehicle Poojas': [],
        'Important Life Samskaras (Ceremonies)': [],
        'Festival & Temple Poojas': [],
        'Homams / Fire Rituals': [],
        'Yagnas (Vedic Offerings)': [],
    }
    
    # Categorize poojas by exact name matching first, then keyword matching
    for pooja in all_poojas:
        pooja_name = pooja.name.strip()
        pooja_name_lower = pooja_name.lower()
        categorized = False
        
        # Match by exact name (case-insensitive) - more flexible matching
        # First check exact name matches
        daily_match = any(daily_name.lower() == pooja_name_lower or 
                         daily_name.lower() in pooja_name_lower or 
                         pooja_name_lower in daily_name.lower() 
                         for daily_name in daily_poojas)
        
        # Also check keyword matching for daily poojas
        keyword_match = any(keyword in pooja_name_lower for keyword in daily_keywords)
        
        if daily_match or keyword_match:
            pooja_categories['Daily & Common Household Poojas'].append(pooja)
            categorized = True
        elif any(house_name.lower() == pooja_name_lower or house_name.lower() in pooja_name_lower for house_name in house_poojas):
            pooja_categories['House, Property & Vehicle Poojas'].append(pooja)
            categorized = True
        elif any(samskara_name.lower() == pooja_name_lower or samskara_name.lower() in pooja_name_lower for samskara_name in samskara_poojas):
            pooja_categories['Important Life Samskaras (Ceremonies)'].append(pooja)
            categorized = True
        elif any(festival_name.lower() == pooja_name_lower or festival_name.lower() in pooja_name_lower for festival_name in festival_poojas):
            pooja_categories['Festival & Temple Poojas'].append(pooja)
            categorized = True
        elif any(homam_name.lower() == pooja_name_lower or homam_name.lower() in pooja_name_lower for homam_name in homam_poojas):
            pooja_categories['Homams / Fire Rituals'].append(pooja)
            categorized = True
        elif any(yagna_name.lower() == pooja_name_lower or yagna_name.lower() in pooja_name_lower for yagna_name in yagna_poojas):
            pooja_categories['Yagnas (Vedic Offerings)'].append(pooja)
            categorized = True
        
        # Fallback to keyword matching if not matched by exact name
        if not categorized:
            if any(keyword in pooja_name_lower for keyword in daily_keywords):
                pooja_categories['Daily & Common Household Poojas'].append(pooja)
                categorized = True
            elif any(keyword in pooja_name_lower for keyword in house_keywords):
                pooja_categories['House, Property & Vehicle Poojas'].append(pooja)
                categorized = True
            elif any(keyword in pooja_name_lower for keyword in samskara_keywords):
                pooja_categories['Important Life Samskaras (Ceremonies)'].append(pooja)
                categorized = True
            elif any(keyword in pooja_name_lower for keyword in festival_keywords):
                pooja_categories['Festival & Temple Poojas'].append(pooja)
                categorized = True
            elif any(keyword in pooja_name_lower for keyword in homam_keywords):
                pooja_categories['Homams / Fire Rituals'].append(pooja)
                categorized = True
            elif any(keyword in pooja_name_lower for keyword in yagna_keywords):
                pooja_categories['Yagnas (Vedic Offerings)'].append(pooja)
                categorized = True
        
        # If still not categorized, add to Daily & Common Household as default
        if not categorized:
            pooja_categories['Daily & Common Household Poojas'].append(pooja)
    
    # Sort poojas within each category to prioritize specific ones
    # For "Daily & Common Household Poojas", ensure specific poojas appear first
    daily_priority_order = [
        'Ganapati Puja', 'Navagraha Puja', 'Satyanarayana Vratam', 
        'Lakshmi Puja', 'Durga Puja', 'Hanuman Puja', 'Rudrabhishekam'
    ]
    
    # For "House, Property & Vehicle Poojas", ensure specific poojas appear first
    house_priority_order = [
        'Bhoomi Puja', 'Gruha Pravesam', 'Gruha Pravesh', 'Vastu Shanti Puja', 'Vehicle Puja'
    ]
    
    if 'Daily & Common Household Poojas' in pooja_categories:
        daily_poojas_list = pooja_categories['Daily & Common Household Poojas']
        # Sort: priority poojas first, then others alphabetically
        daily_poojas_list.sort(key=lambda p: (
            0 if any(priority.lower() in p.name.lower() for priority in daily_priority_order) else 1,
            p.name.lower()
        ))
    
    if 'House, Property & Vehicle Poojas' in pooja_categories:
        house_poojas_list = pooja_categories['House, Property & Vehicle Poojas']
        # Sort: priority poojas first, then others alphabetically
        house_poojas_list.sort(key=lambda p: (
            0 if any(priority.lower() in p.name.lower() for priority in house_priority_order) else 1,
            p.name.lower()
        ))
    
    # Remove empty categories
    context['pooja_categories'] = {k: v for k, v in pooja_categories.items() if v}
    
    # Homepage Explore Pandits: exactly 2 rows of cards (no pagination, no redirect)
    # Grid is col-lg-4 = 3 cards per row on desktop → 2 rows = 6 cards
    HOMEPAGE_PANDIT_ROWS = 2
    CARDS_PER_ROW_DESKTOP = 3
    HOMEPAGE_PANDIT_LIMIT = HOMEPAGE_PANDIT_ROWS * CARDS_PER_ROW_DESKTOP  # 6
    try:
        from profiles.models import PanditProfile
        sample_listings = PanditProfile.objects.filter(
            user__role='pandit',
            user__status='active',
            user__is_active=True,
            is_profile_approved=True,
        ).select_related('user').prefetch_related('cities_served', 'areas_served', 'poojas_performed')[:HOMEPAGE_PANDIT_LIMIT]
        context['sample_listings'] = list(sample_listings) if sample_listings.exists() else None
    except ImportError:
        context['sample_listings'] = None
    
    # Optional: Show reviews context section (backend can control this)
    context['show_reviews_context'] = True  # Backend can make this conditional
    
    return render(request, 'core/home.html', context)