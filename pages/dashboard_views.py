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
from .models_cms import CMSPage, CMSRevision, SiteSEOConfig, SocialMediaSettings, FAQCategory, FAQItem
from .forms_cms import CMSPageForm, SiteSEOConfigForm, SocialMediaSettingsForm, FAQCategoryForm, FAQItemForm


def super_admin_required(view_func):
    """Decorator to ensure only super admins can access CMS views."""
    return user_passes_test(lambda u: u.is_superuser, login_url='/accounts/login/')(view_func)


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

