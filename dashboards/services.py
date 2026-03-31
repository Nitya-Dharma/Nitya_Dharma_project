"""
Dashboard services for Super Admin Dashboard.

UNIT 3: Platform Overview (Read-Only Metrics)
UNIT 4: System Health Snapshot
Provides aggregated counts and health indicators without heavy computation.
"""
from django.db import connection, models
from django.core.cache import cache
from django.conf import settings
from accounts.models import User
from profiles.models import PanditProfile
from pages.models import Page
from booking_intent.models import BookingIntent
import logging

logger = logging.getLogger(__name__)


class DashboardMetricsService:
    """
    Service for computing read-only dashboard metrics.
    
    Rules:
    - Use .count() queries only
    - No joins or heavy aggregation
    - No side effects
    - Fast execution (< 100ms)
    """
    
    @staticmethod
    def get_platform_overview():
        """
        Get platform overview metrics (read-only counts).
        Cached 60s to avoid repeated count queries on every dashboard load (SLOW REQUEST fix).
        
        Returns:
            dict: Platform metrics with counts
        """
        cache_key = 'dashboard:platform_overview'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        result = {
            'total_users': User.objects.filter(role='user', is_active=True).count(),
            'total_pandits': PanditProfile.objects.count(),
            'active_pandits': User.objects.filter(
                role='pandit',
                status='active',
                is_active=True
            ).count(),
            'pending_pandits': User.objects.filter(
                role='pandit',
                status='pending'
            ).count(),
            'pages_count': Page.objects.filter(is_deleted=False).count(),
            'booking_intents_count': BookingIntent.objects.count(),
        }
        cache.set(cache_key, result, 60)
        return result
    
    @staticmethod
    def get_system_health():
        """
        Get system health snapshot (UNIT 4).
        
        Checks:
        - Database connection
        - Cache status (if configured)
        - Background jobs status (placeholder)
        
        Rules:
        - Lightweight checks only
        - Timeouts ≤ 100ms
        - Fail silently with "Unknown" status
        - No sensitive data exposed
        
        Returns:
            dict: Health indicators with status and value
        """
        health_indicators = []
        
        # Database Health Check
        db_status = 'Unknown'
        db_value = 'Not checked'
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            db_status = 'healthy'
            db_value = 'Connected'
        except Exception as e:
            db_status = 'unhealthy'
            db_value = 'Disconnected'
            logger.warning(f"Database health check failed: {str(e)}")
        
        health_indicators.append({
            'label': 'Database',
            'status': db_status,
            'value': db_value,
        })
        
        # Cache Health Check (if configured)
        cache_status = 'Unknown'
        cache_value = 'Not configured'
        if hasattr(settings, 'CACHES') and settings.CACHES:
            try:
                # Try to set and get a test value (with timeout)
                test_key = 'health_check_test'
                test_value = 'test'
                cache.set(test_key, test_value, timeout=1)
                retrieved = cache.get(test_key)
                if retrieved == test_value:
                    cache_status = 'healthy'
                    cache_value = 'OK'
                else:
                    cache_status = 'degraded'
                    cache_value = 'Degraded'
                cache.delete(test_key)  # Clean up
            except Exception as e:
                cache_status = 'unhealthy'
                cache_value = 'Error'
                logger.warning(f"Cache health check failed: {str(e)}")
        else:
            cache_status = 'not_configured'
            cache_value = 'Not configured'
        
        health_indicators.append({
            'label': 'Cache',
            'status': cache_status,
            'value': cache_value,
        })
        
        # Background Jobs Status (placeholder - no background jobs system yet)
        health_indicators.append({
            'label': 'Background Jobs',
            'status': 'not_configured',
            'value': 'Not configured',
        })
        
        return health_indicators
    
    @staticmethod
    def get_pandit_governance_list(status_filter=None, search_query=None):
        """
        Get Pandit governance overview list (UNIT 7).
        
        Returns read-only listing of all Pandits with:
        - Name
        - City
        - Current status
        - Joined date
        - Last updated
        - Referred by (if any)
        
        Args:
            status_filter (str, optional): Filter by status (pending/active/rejected/suspended)
            search_query (str, optional): Search by name/email
        
        Returns:
            QuerySet: PanditProfile queryset with related data
        """
        from profiles.models import PanditProfile
        
        # Base query with essential joins only; defer heavy columns to avoid slow SELECT (Phase 12 slow-query fix)
        # Note: cities_served is ManyToMany, not ForeignKey, so use prefetch_related
        queryset = PanditProfile.objects.select_related(
            'user',
            'user__referred_by'
        ).prefetch_related(
            'cities_served'  # ManyToMany field, not ForeignKey
        ).defer(
            'about_description',
            'languages_spoken',
            'profile_image',
            'cover_image',
            'seo_description',
            'seo_keywords',
        ).all()
        
        # Apply status filter
        if status_filter:
            queryset = queryset.filter(user__status=status_filter)
        
        # Apply search query
        if search_query:
            queryset = queryset.filter(
                models.Q(display_name__icontains=search_query) |
                models.Q(user__email__icontains=search_query) |
                models.Q(user__first_name__icontains=search_query) |
                models.Q(user__last_name__icontains=search_query)
            )
        
        return queryset.order_by('-user__date_joined')
    
    @staticmethod
    def get_seo_oversight_list(entity_type='all', search_query=None):
        """
        Get SEO metadata oversight list (UNIT 15).
        
        Returns read-only listing of SEO metadata for:
        - Pandit Profiles
        - Pages
        
        Args:
            entity_type (str): Filter by entity type ('pandit', 'page', 'all')
            search_query (str, optional): Search by name/title
        
        Returns:
            list: List of dicts with SEO metadata
        """
        seo_list = []
        
        # Cap result size to avoid slow dashboard load (SLOW REQUEST fix)
        SEO_OVERSIGHT_MAX_PER_TYPE = 1000
        
        # Get Pandit Profiles SEO
        if entity_type in ['pandit', 'all']:
            from profiles.models import PanditProfile
            pandit_profiles = (
                PanditProfile.objects.select_related('user')
                .prefetch_related('cities_served')
                .order_by('-updated_at')
            )
            if search_query:
                pandit_profiles = pandit_profiles.filter(
                    Q(display_name__icontains=search_query) |
                    Q(user__email__icontains=search_query)
                )
            pandit_profiles = pandit_profiles[:SEO_OVERSIGHT_MAX_PER_TYPE]
            
            for profile in pandit_profiles:
                seo_list.append({
                    'entity_type': 'Pandit',
                    'entity_id': profile.id,
                    'entity_public_id': profile.public_id,
                    'entity_name': profile.get_display_name() or profile.user.email,
                    'seo_title': profile.seo_title,
                    'seo_description': profile.seo_description,
                    'seo_keywords': profile.seo_keywords,
                    'seo_autogenerated': profile.seo_autogenerated,
                    'seo_last_updated_at': getattr(profile, 'seo_last_updated_at', None),
                    'entity': profile,
                })
        
        # Get Pages SEO
        if entity_type in ['page', 'all']:
            from pages.models import Page
            pages = (
                Page.objects.select_related('created_by')
                .order_by('-updated_at')
            )
            if search_query:
                pages = pages.filter(
                    Q(title__icontains=search_query) |
                    Q(slug__icontains=search_query)
                )
            pages = pages[:SEO_OVERSIGHT_MAX_PER_TYPE]
            
            for page in pages:
                seo_list.append({
                    'entity_type': 'Page',
                    'entity_id': page.id,
                    'entity_public_id': page.public_id,
                    'entity_name': page.title,
                    'seo_title': page.seo_title,
                    'seo_description': page.seo_description,
                    'seo_keywords': page.seo_keywords,
                    'seo_autogenerated': page.seo_autogenerated,
                    'seo_last_updated_at': getattr(page, 'seo_last_updated_at', None),
                    'entity': page,
                })
        
        # Sort by last updated (newest first)
        seo_list.sort(
            key=lambda x: x['seo_last_updated_at'] or x['entity'].updated_at if hasattr(x['entity'], 'updated_at') else x['entity'].created_at,
            reverse=True
        )
        
        return seo_list
    
    @staticmethod
    def get_crawl_readiness_indicators():
        """
        Get crawl readiness indicators for public entities (UNIT 16).
        
        Returns read-only indicators for:
        - Pandit Profiles
        - Pages
        
        Indicators:
        - Public URL
        - Meta tags present (yes/no)
        - JSON-LD present (yes/no)
        - Canonical URL present (yes/no)
        - Visibility status
        
        Returns:
            list: List of dicts with crawl readiness data
        """
        from django.conf import settings
        from django.urls import reverse
        
        crawl_list = []
        base_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        
        # Get Pandit Profiles
        from profiles.models import PanditProfile
        pandit_profiles = PanditProfile.objects.select_related('user').prefetch_related(
            'cities_served'
        ).all()
        
        for profile in pandit_profiles:
            # Check if profile is public (user is active)
            is_public = profile.user.status == 'active'
            
            # Build public URL
            try:
                public_url = f"{base_url}{reverse('profiles:profile_public', args=[profile.public_id])}"
            except:
                public_url = f"{base_url}/profiles/{profile.public_id}/"
            
            # Check meta tags
            has_meta_title = bool(profile.seo_title)
            has_meta_description = bool(profile.seo_description)
            has_meta_keywords = bool(profile.seo_keywords)
            meta_tags_present = has_meta_title and has_meta_description
            
            # JSON-LD is generated dynamically, so always present if profile exists
            json_ld_present = True
            
            # Canonical URL (using public_id URL as canonical)
            canonical_url_present = True
            
            crawl_list.append({
                'entity_type': 'Pandit',
                'entity_id': profile.id,
                'entity_public_id': profile.public_id,
                'entity_name': profile.get_display_name() or profile.user.email,
                'public_url': public_url,
                'meta_tags_present': meta_tags_present,
                'json_ld_present': json_ld_present,
                'canonical_url_present': canonical_url_present,
                'visibility_status': 'public' if is_public else 'private',
                'has_meta_title': has_meta_title,
                'has_meta_description': has_meta_description,
                'has_meta_keywords': has_meta_keywords,
            })
        
        # Get Pages
        from pages.models import Page
        pages = Page.objects.select_related('created_by').all()
        
        for page in pages:
            # Check if page is public (status is ACTIVE)
            is_public = page.status == 'ACTIVE' and not page.is_deleted
            
            # Build public URL
            try:
                public_url = f"{base_url}{reverse('pages:page_detail', args=[page.slug])}"
            except:
                public_url = f"{base_url}/pages/{page.slug}/"
            
            # Check meta tags
            has_meta_title = bool(page.seo_title)
            has_meta_description = bool(page.seo_description)
            has_meta_keywords = bool(page.seo_keywords)
            meta_tags_present = has_meta_title and has_meta_description
            
            # JSON-LD is generated dynamically, so always present if page exists
            json_ld_present = True
            
            # Canonical URL (using public_id URL as canonical)
            canonical_url_present = True
            
            crawl_list.append({
                'entity_type': 'Page',
                'entity_id': page.id,
                'entity_public_id': page.public_id,
                'entity_name': page.title,
                'public_url': public_url,
                'meta_tags_present': meta_tags_present,
                'json_ld_present': json_ld_present,
                'canonical_url_present': canonical_url_present,
                'visibility_status': 'public' if is_public else 'private',
                'has_meta_title': has_meta_title,
                'has_meta_description': has_meta_description,
                'has_meta_keywords': has_meta_keywords,
            })
        
        return crawl_list
    
    @staticmethod
    def get_referral_chain_for_pandit(pandit_user):
        """
        Get referral chain and trust visibility data for a Pandit (UNIT 10).
        
        Returns read-only trust signals:
        - Referrer Pandit
        - Referral depth
        - Verification milestones
        - Complaints count (if any)
        
        Args:
            pandit_user: User instance with role='pandit'
        
        Returns:
            dict: Referral chain and trust data (read-only, no scoring)
        """
        from trust_display.selectors import get_referral_chain_for_pandit, get_governance_state_for_pandit
        
        # Get referral chain data (read-only)
        referral_chain = get_referral_chain_for_pandit(pandit_user)
        
        # Get governance state (includes complaints/flags)
        governance_state = get_governance_state_for_pandit(pandit_user)
        
        # Build trust visibility data (read-only, no scoring)
        trust_data = {
            'referrer': referral_chain.get('referrer'),
            'referral_depth': referral_chain.get('chain_length', 0),
            'has_referral': referral_chain.get('has_referral', False),
            'flagged_reviews_count': governance_state.get('flagged_reviews_count', 0),
            'flagged_intents_count': governance_state.get('flagged_intents_count', 0),
            'has_complaints': (
                governance_state.get('flagged_reviews_count', 0) > 0 or
                governance_state.get('flagged_intents_count', 0) > 0
            ),
        }
        
        return trust_data
    
    @staticmethod
    def get_seo_oversight_list(entity_type='all', search_query=None):
        """
        Get SEO metadata oversight list (UNIT 15).
        
        Returns SEO metadata for Pandit Profiles and Pages:
        - SEO title, description, keywords
        - Auto-generated vs manually edited flag
        - Last SEO update time
        
        Args:
            entity_type (str): 'pandit', 'page', or 'all'
            search_query (str, optional): Search by name/title
        
        Returns:
            dict: {'pandits': [...], 'pages': [...]}
        """
        seo_data = {'pandits': [], 'pages': []}
        
        if entity_type in ['pandit', 'all']:
            from profiles.models import PanditProfile
            pandit_query = PanditProfile.objects.select_related('user').prefetch_related('cities_served')
            
            if search_query:
                pandit_query = pandit_query.filter(
                    models.Q(display_name__icontains=search_query) |
                    models.Q(user__email__icontains=search_query) |
                    models.Q(user__first_name__icontains=search_query) |
                    models.Q(user__last_name__icontains=search_query)
                )
            
            for profile in pandit_query[:100]:  # Limit to 100 for performance
                seo_data['pandits'].append({
                    'id': profile.id,
                    'public_id': profile.public_id,
                    'name': profile.get_display_name() or profile.user.get_full_name() or profile.user.email,
                    'seo_title': profile.seo_title,
                    'seo_description': profile.seo_description,
                    'seo_keywords': profile.seo_keywords,
                    'seo_autogenerated': profile.seo_autogenerated,
                    'seo_last_updated_at': profile.seo_last_updated_at,
                    'entity_type': 'PanditProfile',
                })
        
        if entity_type in ['page', 'all']:
            from pages.models import Page
            page_query = Page.objects.select_related('created_by').filter(is_deleted=False)
            
            if search_query:
                page_query = page_query.filter(
                    models.Q(title__icontains=search_query) |
                    models.Q(created_by__email__icontains=search_query)
                )
            
            for page in page_query[:100]:  # Limit to 100 for performance
                seo_data['pages'].append({
                    'id': page.id,
                    'public_id': page.public_id,
                    'title': page.title,
                    'page_type': page.page_type,
                    'seo_title': page.seo_title,
                    'seo_description': page.seo_description,
                    'seo_keywords': page.seo_keywords,
                    'seo_autogenerated': page.seo_autogenerated,
                    'seo_last_updated_at': page.seo_last_updated_at,
                    'entity_type': 'Page',
                })
        
        return seo_data

