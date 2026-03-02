"""
CMS Forms for Dashboard-based content management.
"""
from django import forms
from .models_cms import CMSPage, SiteSEOConfig, SocialMediaSettings, FAQCategory, FAQItem


class CMSPageForm(forms.ModelForm):
    """Form for editing CMS pages in dashboard."""
    
    class Meta:
        model = CMSPage
        fields = [
            'title',
            'content',
            'seo_title',
            'seo_description',
            'seo_keywords',
            'og_image',
            'is_published',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Page title (H1)',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 20,
                'placeholder': 'Page content (HTML allowed)',
            }),
            'seo_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SEO title (50-60 characters recommended)',
                'maxlength': '255',
            }),
            'seo_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'SEO description (140-160 characters recommended)',
                'maxlength': '500',
            }),
            'seo_keywords': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'SEO keywords (comma-separated)',
            }),
            'og_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make SEO fields optional
        self.fields['seo_title'].required = False
        self.fields['seo_description'].required = False
        self.fields['seo_keywords'].required = False
        self.fields['og_image'].required = False


class SiteSEOConfigForm(forms.ModelForm):
    """Form for editing global SEO configuration."""
    
    class Meta:
        model = SiteSEOConfig
        fields = [
            'organization_name',
            'organization_logo',
            'default_og_image',
            'twitter_handle',
        ]
        widgets = {
            'organization_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Organization name',
            }),
            'organization_logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'default_og_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'twitter_handle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '@twitterhandle',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields optional
        self.fields['organization_name'].required = False
        self.fields['organization_logo'].required = False
        self.fields['default_og_image'].required = False
        self.fields['twitter_handle'].required = False


class SocialMediaSettingsForm(forms.ModelForm):
    """Form for editing social media links in dashboard."""
    
    class Meta:
        model = SocialMediaSettings
        fields = [
            'facebook_url',
            'instagram_url',
            'twitter_url',
            'linkedin_url',
            'youtube_url',
            'threads_url',
        ]
        widgets = {
            'facebook_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://facebook.com/yourpage',
            }),
            'instagram_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://instagram.com/yourprofile',
            }),
            'twitter_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/yourhandle',
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/company/yourcompany',
            }),
            'youtube_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://youtube.com/@yourchannel',
            }),
            'threads_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://threads.net/@yourprofile',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional
        for field in self.fields:
            self.fields[field].required = False


class FAQCategoryForm(forms.ModelForm):
    """Form for editing FAQ categories."""
    
    class Meta:
        model = FAQCategory
        fields = ['name', 'order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category name (e.g., General, Booking, Pandits)',
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Display order (lower numbers appear first)',
            }),
        }


class FAQItemForm(forms.ModelForm):
    """Form for editing FAQ items."""
    
    class Meta:
        model = FAQItem
        fields = ['category', 'question', 'answer', 'order', 'is_published']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-control',
            }),
            'question': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'FAQ question (displayed in accordion header)',
                'maxlength': '300',
            }),
            'answer': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'FAQ answer (HTML allowed, displayed in accordion body)',
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Display order (lower numbers appear first)',
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make category optional
        self.fields['category'].required = False
        self.fields['category'].queryset = FAQCategory.objects.all().order_by('order', 'name')

