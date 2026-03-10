"""
Dashboard-based CMS management views for Super Admin.
Replaces Django admin CMS interface.
"""
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import Http404
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import get_user_model
from .models_cms import CMSPage, CMSRevision, SiteSEOConfig, SocialMediaSettings, FAQCategory, FAQItem
from .forms_cms import CMSPageForm, SiteSEOConfigForm, SocialMediaSettingsForm, FAQCategoryForm, FAQItemForm

User = get_user_model()


def super_admin_required(view_func):
    """Decorator to ensure only super admins can access CMS views."""
    return user_passes_test(lambda u: u.is_superuser, login_url='/accounts/login/')(view_func)


# Default CMS page definitions (same as init_cms_pages management command)
CMS_INITIAL_PAGES = [
    {
        'page_type': 'about',
        'title': 'About Nitya Dharma',
        'slug': 'about-us',
        'content': '<h2>Our Mission</h2><p>Nitya Dharma is India\'s premier digital platform connecting devotees with verified and trusted pandits for authentic religious ceremonies, poojas, and spiritual services.</p><h2>What We Offer</h2><p>We provide a transparent, secure platform where users can discover, verify, and book qualified pandits for their spiritual needs.</p><h2>Why Choose Us</h2><p>All pandits on our platform are verified, ensuring quality, authenticity, and cultural respect in every service.</p>',
        'seo_title': 'About Nitya Dharma | Verified Pandit Platform',
        'seo_description': 'Learn about Nitya Dharma, a trusted platform connecting devotees with verified pandits and temples across India.',
        'seo_keywords': 'about nitya dharma, pandit platform, religious ceremonies, pooja services',
    },
    {
        'page_type': 'terms',
        'title': 'Terms and Conditions',
        'slug': 'terms-and-conditions',
        'content': '<h2>User Responsibilities</h2><p>Users must provide accurate information and use the platform responsibly.</p><h2>Pandit Responsibilities</h2><p>Pandits must maintain accurate profiles and deliver services as described.</p><h2>Platform Limitations</h2><p>Nitya Dharma is a platform connecting users and pandits. We are not responsible for the quality of services provided by individual pandits.</p><h2>Content Policy</h2><p>All content must be respectful and comply with our community guidelines.</p><h2>Liability</h2><p>Users and pandits are responsible for their own interactions and agreements.</p><h2>Governing Law</h2><p>These terms are governed by Indian law.</p>',
        'seo_title': 'Terms and Conditions - Nitya Dharma',
        'seo_description': 'Read Nitya Dharma\'s Terms and Conditions. Understand user responsibilities, platform policies, and governing laws.',
        'seo_keywords': 'terms and conditions, user agreement, platform terms',
    },
    {
        'page_type': 'privacy',
        'title': 'Privacy Policy',
        'slug': 'privacy-policy',
        'content': '<h2>Information We Collect</h2><p>We collect information you provide, such as name, email, phone number, and service preferences.</p><h2>How We Use Information</h2><p>We use your information to provide services, improve our platform, and communicate with you.</p><h2>Data Security</h2><p>We implement security measures to protect your personal information.</p><h2>Cookies</h2><p>We use cookies to enhance your experience and analyze platform usage.</p><h2>Third-Party Services</h2><p>We may use third-party services that have their own privacy policies.</p><h2>User Rights</h2><p>You have the right to access, update, or delete your personal information.</p><h2>Contact Information</h2><p>For privacy concerns, please contact us through our contact form.</p>',
        'seo_title': 'Privacy Policy - Nitya Dharma | Data Protection',
        'seo_description': 'Nitya Dharma Privacy Policy. Learn how we collect, use, and protect your personal information. Understand your privacy rights.',
        'seo_keywords': 'privacy policy, data protection, privacy rights',
    },
]


@super_admin_required
@require_POST
@csrf_protect
def cms_init_defaults(request):
    """Create default CMS pages (About Us, Terms, Privacy Policy) if they don't exist. Super Admin only."""
    superuser = User.objects.filter(is_superuser=True).first()
    if not superuser:
        messages.error(request, 'No superuser found. Cannot create default pages.')
        return redirect('pages:super_admin_cms_list')
    SiteSEOConfig.objects.get_or_create(pk=1, defaults={'organization_name': 'Nitya Dharma'})
    created_count = 0
    for page_data in CMS_INITIAL_PAGES:
        data = dict(page_data)
        page_type = data.pop('page_type')
        page, created = CMSPage.objects.get_or_create(
            page_type=page_type,
            defaults={
                **data,
                'created_by': superuser,
                'updated_by': superuser,
                'is_published': False,
            },
        )
        if created:
            created_count += 1
    if created_count:
        messages.success(request, f'Created {created_count} default CMS page(s). You can now edit and publish About Us, Privacy Policy, and Terms and Conditions.')
    else:
        messages.info(request, 'Default CMS pages already exist. Use the Edit links below to manage them.')
    return redirect('pages:super_admin_cms_list')


@super_admin_required
def cms_list(request):
    """List all CMS pages."""
    pages = CMSPage.objects.all().order_by('page_type')
    context = {
        'pages': pages,
        'user_role': 'super_admin',
        'dashboard_has_data': True,  # Required by dashboard_base.html
        'dashboard_loading': False,
        'dashboard_error': None,
    }
    return render(request, 'dashboard/super_admin/cms_list.html', context)


@super_admin_required
def cms_edit(request, slug):
    """Edit a CMS page."""
    page = get_object_or_404(CMSPage, slug=slug)
    
    if request.method == "POST":
        form = CMSPageForm(request.POST, request.FILES, instance=page)
        if form.is_valid():
            try:
                # Set updated_by before saving
                page.updated_by = request.user
                
                # Handle publishing
                if form.cleaned_data.get('is_published') and not page.is_published:
                    page.published_at = timezone.now()
                elif not form.cleaned_data.get('is_published'):
                    page.published_at = None
                
                form.save()
                messages.success(request, f"CMS page '{page.title}' saved successfully.")
                return redirect('pages:super_admin_cms_list')
            except ValidationError as e:
                messages.error(request, f"Validation error: {e}")
    else:
        form = CMSPageForm(instance=page)
    
    context = {
        'form': form,
        'page': page,
        'user_role': 'super_admin',
        'dashboard_has_data': True,  # Required by dashboard_base.html
        'dashboard_loading': False,
        'dashboard_error': None,
    }
    return render(request, 'dashboard/super_admin/cms_edit.html', context)


@super_admin_required
def cms_revisions(request, slug):
    """View revision history for a CMS page."""
    page = get_object_or_404(CMSPage, slug=slug)
    revisions = page.revisions.all().order_by('-created_at')
    
    context = {
        'page': page,
        'revisions': revisions,
        'user_role': 'super_admin',
        'dashboard_has_data': True,  # Required by dashboard_base.html
        'dashboard_loading': False,
        'dashboard_error': None,
    }
    return render(request, 'dashboard/super_admin/cms_revisions.html', context)


@super_admin_required
def cms_seo_config(request):
    """Edit global SEO configuration."""
    seo_config, created = SiteSEOConfig.objects.get_or_create(pk=1)
    
    if request.method == "POST":
        form = SiteSEOConfigForm(request.POST, request.FILES, instance=seo_config)
        if form.is_valid():
            form.save()
            messages.success(request, "SEO configuration saved successfully.")
            return redirect('pages:super_admin_cms_seo_config')
    else:
        form = SiteSEOConfigForm(instance=seo_config)
    
    context = {
        'form': form,
        'seo_config': seo_config,
        'user_role': 'super_admin',
        'dashboard_has_data': True,  # Required by dashboard_base.html
        'dashboard_loading': False,
        'dashboard_error': None,
    }
    return render(request, 'dashboard/super_admin/cms_seo_config.html', context)


@super_admin_required
def cms_social_settings(request):
    """Edit global social media links."""
    social_settings = SocialMediaSettings.load()
    
    if request.method == "POST":
        form = SocialMediaSettingsForm(request.POST, instance=social_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Social media links updated successfully.")
            return redirect('pages:super_admin_social_settings')
    else:
        form = SocialMediaSettingsForm(instance=social_settings)
    
    context = {
        'form': form,
        'social_settings': social_settings,
        'user_role': 'super_admin',
        'dashboard_has_data': True,  # Required by dashboard_base.html
        'dashboard_loading': False,
        'dashboard_error': None,
    }
    return render(request, 'dashboard/super_admin/cms_social_settings.html', context)


@super_admin_required
def faq_list(request):
    """List all FAQ items grouped by category."""
    categories = FAQCategory.objects.prefetch_related('faqs').all().order_by('order', 'name')
    uncategorized_faqs = FAQItem.objects.filter(category=None).order_by('order', 'question')
    
    context = {
        'categories': categories,
        'uncategorized_faqs': uncategorized_faqs,
        'user_role': 'super_admin',
        'dashboard_has_data': True,
        'dashboard_loading': False,
        'dashboard_error': None,
    }
    return render(request, 'dashboard/super_admin/faq_list.html', context)


@super_admin_required
def faq_create(request):
    """Create a new FAQ item."""
    if request.method == "POST":
        form = FAQItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "FAQ created successfully.")
            return redirect('pages:super_admin_faq_list')
        else:
            messages.error(request, "Error creating FAQ. Please check the form.")
    else:
        form = FAQItemForm()
    
    context = {
        'form': form,
        'user_role': 'super_admin',
        'dashboard_has_data': True,
        'dashboard_loading': False,
        'dashboard_error': None,
    }
    return render(request, 'dashboard/super_admin/faq_form.html', context)


@super_admin_required
def faq_edit(request, pk):
    """Edit an existing FAQ item."""
    faq = get_object_or_404(FAQItem, pk=pk)
    
    if request.method == "POST":
        form = FAQItemForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            messages.success(request, "FAQ updated successfully.")
            return redirect('pages:super_admin_faq_list')
        else:
            messages.error(request, "Error updating FAQ. Please check the form.")
    else:
        form = FAQItemForm(instance=faq)
    
    context = {
        'form': form,
        'faq': faq,
        'user_role': 'super_admin',
        'dashboard_has_data': True,
        'dashboard_loading': False,
        'dashboard_error': None,
    }
    return render(request, 'dashboard/super_admin/faq_form.html', context)


@super_admin_required
def faq_delete(request, pk):
    """Delete an FAQ item."""
    faq = get_object_or_404(FAQItem, pk=pk)
    
    if request.method == "POST":
        question = faq.question
        faq.delete()
        messages.success(request, f"FAQ '{question}' deleted successfully.")
        return redirect('pages:super_admin_faq_list')
    
    context = {
        'faq': faq,
        'user_role': 'super_admin',
        'dashboard_has_data': True,
        'dashboard_loading': False,
        'dashboard_error': None,
    }
    return render(request, 'dashboard/super_admin/faq_delete.html', context)

