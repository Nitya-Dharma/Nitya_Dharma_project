"""
Static SEO-optimized pages views.
About Us, Terms & Conditions, Privacy Policy, Contact Us (SEO optimization)
Uses WordPress-style CMS model if available, falls back to template-only rendering.
"""
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.http import Http404
from .models_cms import CMSPage, SiteSEOConfig, FAQCategory, FAQItem


def get_base_url(request):
    """Get base URL for canonical and OG tags."""
    return request.build_absolute_uri('/').rstrip('/')


def static_page_detail(request, slug):
    """
    Generic static page view using WordPress-style CMS model.
    Only allows specific slugs for security.
    Maintains same URLs as before.
    """
    # Security: Only allow specific slugs
    allowed_slugs = ['about-us', 'terms-and-conditions', 'privacy-policy']
    if slug not in allowed_slugs:
        raise Http404("Page not found")
    
    # Map slug to page_type
    slug_to_type = {
        'about-us': 'about',
        'terms-and-conditions': 'terms',
        'privacy-policy': 'privacy',
    }
    
    page_type = slug_to_type.get(slug)
    
    # Try to get from CMS, fallback to template-only
    try:
        page = CMSPage.objects.get(page_type=page_type, is_published=True)
        
        base_url = get_base_url(request)
        canonical_url = f"{base_url}/{slug}/"
        
        # Get SEO config if available
        seo_config = SiteSEOConfig.objects.first()
        
        # Use CMS data
        seo_context = {
            'seo_title': page.seo_title or page.title,
            'seo_description': page.seo_description or '',
            'seo_keywords': page.seo_keywords or '',
            'canonical_url': canonical_url,
            'og_title': page.seo_title or page.title,
            'og_description': page.seo_description or '',
            'og_type': 'website',
            'og_image': page.og_image.url if page.og_image else (seo_config.default_og_image.url if seo_config and seo_config.default_og_image else ''),
            'page': page,  # Pass page object to template
            'use_cms': True,
        }
        
        # Use unified CMS template
        return render(request, 'pages/cms_page.html', seo_context)
        
    except CMSPage.DoesNotExist:
        # Fallback to original template-only rendering
        return _render_fallback(request, slug)


def _render_fallback(request, slug):
    """Fallback rendering when CMS page doesn't exist."""
    base_url = get_base_url(request)
    canonical_url = f"{base_url}/{slug}/"
    
    # Default SEO for each page
    defaults = {
        'about-us': {
            'seo_title': 'About Us - Nitya Dharma | Connecting You with Trusted Pandits',
            'seo_description': 'Learn about Nitya Dharma, India\'s premier platform connecting devotees with verified pandits for authentic religious ceremonies and poojas.',
            'seo_keywords': 'about nitya dharma, pandit platform, religious ceremonies, pooja services',
            'og_title': 'About Nitya Dharma - Connecting You with Trusted Pandits',
            'og_description': 'Learn about Nitya Dharma, India\'s premier platform connecting devotees with verified pandits.',
        },
        'terms-and-conditions': {
            'seo_title': 'Terms and Conditions - Nitya Dharma',
            'seo_description': 'Read Nitya Dharma\'s Terms and Conditions. Understand user responsibilities and platform policies.',
            'seo_keywords': 'terms and conditions, user agreement, platform terms',
            'og_title': 'Terms and Conditions - Nitya Dharma',
            'og_description': 'Read Nitya Dharma\'s Terms and Conditions.',
        },
        'privacy-policy': {
            'seo_title': 'Privacy Policy - Nitya Dharma | Data Protection & Privacy',
            'seo_description': 'Nitya Dharma Privacy Policy. Learn how we collect, use, and protect your personal information.',
            'seo_keywords': 'privacy policy, data protection, privacy rights',
            'og_title': 'Privacy Policy - Nitya Dharma',
            'og_description': 'Learn how Nitya Dharma collects, uses, and protects your personal information.',
        },
    }
    
    default_seo = defaults.get(slug, {})
    seo_context = {
        'seo_title': default_seo.get('seo_title', ''),
        'seo_description': default_seo.get('seo_description', ''),
        'seo_keywords': default_seo.get('seo_keywords', ''),
        'canonical_url': canonical_url,
        'og_title': default_seo.get('og_title', ''),
        'og_description': default_seo.get('og_description', ''),
        'og_type': 'website',
        'og_image': '',
        'use_cms': False,
    }
    
    template_name = f'pages/static/{slug.replace("-", "_")}.html'
    return render(request, template_name, seo_context)


def about_us(request):
    """
    About Us page - SEO optimized for Discover, PAA, AEO, GEO, SXO
    Uses WordPress-style CMS model if available.
    URL: /about-us/ (unchanged)
    """
    return static_page_detail(request, 'about-us')


def terms_conditions(request):
    """
    Terms & Conditions page - Legal compliance + SEO
    Uses WordPress-style CMS model if available.
    URL: /terms-and-conditions/ (unchanged)
    """
    return static_page_detail(request, 'terms-and-conditions')


def privacy_policy(request):
    """
    Privacy Policy page - Google AdSense/Discover compliant + SEO
    Uses WordPress-style CMS model if available.
    URL: /privacy-policy/ (unchanged)
    """
    return static_page_detail(request, 'privacy-policy')


def public_faq(request):
    """
    Public FAQ page with accordion UI.
    SEO optimized with FAQPage structured data.
    URL: /faq/
    """
    # Get all categories with published FAQs
    categories = FAQCategory.objects.prefetch_related(
        'faqs'
    ).filter(
        faqs__is_published=True
    ).distinct().order_by('order', 'name')
    
    # Get uncategorized published FAQs
    uncategorized_faqs = FAQItem.objects.filter(
        category=None,
        is_published=True
    ).order_by('order', 'question')
    
    # Build FAQPage schema for SEO
    faq_schema_items = []
    for category in categories:
        for faq in category.faqs.filter(is_published=True):
            faq_schema_items.append({
                "@type": "Question",
                "name": faq.question,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": faq.answer
                }
            })
    
    for faq in uncategorized_faqs:
        faq_schema_items.append({
            "@type": "Question",
            "name": faq.question,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": faq.answer
            }
        })
    
    base_url = get_base_url(request)
    canonical_url = f"{base_url}/faq/"
    
    # Get SEO config if available
    seo_config = SiteSEOConfig.objects.first()
    
    context = {
        'categories': categories,
        'uncategorized_faqs': uncategorized_faqs,
        'faq_schema_items': faq_schema_items,
        'seo_title': 'Frequently Asked Questions (FAQ) - Nitya Dharma',
        'seo_description': 'Find answers to common questions about Nitya Dharma, booking pandits, pooja services, and more.',
        'seo_keywords': 'FAQ, frequently asked questions, pandit booking, pooja services, help',
        'canonical_url': canonical_url,
        'og_title': 'FAQ - Frequently Asked Questions | Nitya Dharma',
        'og_description': 'Find answers to common questions about Nitya Dharma, booking pandits, and pooja services.',
        'og_type': 'website',
        'og_image': seo_config.default_og_image.url if seo_config and seo_config.default_og_image else '',
    }
    
    return render(request, 'pages/faq.html', context)

