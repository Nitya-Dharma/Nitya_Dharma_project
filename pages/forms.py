"""
Django forms for page creation and editing.
"""
from django import forms
from .models import Page
from .constants import PAGE_TYPE_CHOICES, PAGE_TYPE_TEMPLE
from masterdata.models import City, LocalArea


class PageCreateForm(forms.ModelForm):
    """
    Form for creating a new page.
    
    Fields:
    - page_type: Required, filtered by user role
    - title: Required, unlimited length
    - slug: Optional, auto-generated if empty
    - description: Optional
    - address: Optional
    - profile_image: Optional
    - cover_image: Optional
    """
    
    class Meta:
        model = Page
        fields = ['page_type', 'title', 'slug', 'description', 'address', 'city', 'area', 'profile_image', 'cover_image', 
                  'seo_title', 'seo_description', 'seo_keywords']
        # owner_role is NOT in fields - it will be set in backend before save
        widgets = {
            'page_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'pattern': '[a-z0-9-]+'}),
            'description': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'city': forms.Select(attrs={'class': 'form-select'}),
            'area': forms.Select(attrs={'class': 'form-select'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'seo_title': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '60'}),
            'seo_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'maxlength': '160'}),
            'seo_keywords': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.allowed_page_types = kwargs.pop('allowed_page_types', [PAGE_TYPE_TEMPLE])
        super().__init__(*args, **kwargs)
        
        # Exclude owner_role from form validation - it will be set in backend
        if 'owner_role' in self.fields:
            del self.fields['owner_role']
        
        # Filter page_type choices based on user role
        filtered_choices = [
            (pt, label) for pt, label in PAGE_TYPE_CHOICES 
            if pt in self.allowed_page_types
        ]
        
        # Add empty option only if there are multiple choices
        if len(filtered_choices) > 1:
            self.fields['page_type'].choices = [('', 'Select page type...')] + filtered_choices
        else:
            self.fields['page_type'].choices = filtered_choices
        
        # Auto-select if only one option is available (e.g., admin_pandit can only create TEMPLE)
        if len(self.allowed_page_types) == 1:
            # Set initial value if form is not bound (GET request)
            if not self.is_bound:
                self.initial['page_type'] = self.allowed_page_types[0]
                self.fields['page_type'].initial = self.allowed_page_types[0]
            elif self.is_bound and not self.data.get('page_type'):
                # If form is bound but no page_type in POST data, set it in the data
                # This ensures the value is submitted even if the select is auto-selected
                if hasattr(self.data, '_mutable'):
                    self.data._mutable = True
                if isinstance(self.data, dict):
                    self.data = self.data.copy()
                    self.data['page_type'] = self.allowed_page_types[0]
                else:
                    # For QueryDict, use setlist
                    self.data.setlist('page_type', [self.allowed_page_types[0]])
                self.initial['page_type'] = self.allowed_page_types[0]
                self.fields['page_type'].initial = self.allowed_page_types[0]
        
        # Make slug optional
        self.fields['slug'].required = False
        self.fields['slug'].help_text = "Auto-generated from title if left empty"
        
        # Make other fields optional
        self.fields['description'].required = False
        # Address is required (model-level and form-level)
        self.fields['address'].required = True
        self.fields['city'].required = False
        self.fields['area'].required = False
        self.fields['profile_image'].required = False
        self.fields['cover_image'].required = False
        
        # Populate city and area choices
        self.fields['city'].queryset = City.objects.all().order_by('name')
        self.fields['area'].queryset = LocalArea.objects.all().order_by('name')
        
        # Add empty label
        self.fields['city'].empty_label = 'Select City'
        self.fields['area'].empty_label = 'Select Area'
        
        # SEO fields - optional, auto-generated
        self.fields['seo_title'].required = False
        self.fields['seo_title'].help_text = "SEO title (max 60 characters, auto-generated if empty)"
        self.fields['seo_description'].required = False
        self.fields['seo_description'].help_text = "SEO description (max 160 characters, auto-generated if empty)"
        self.fields['seo_keywords'].required = False
        self.fields['seo_keywords'].help_text = "SEO keywords (comma-separated, unlimited length, auto-generated if empty)"
        
        # Auto-generate SEO if instance exists and SEO is empty
        if self.instance and self.instance.pk:
            from .seo_services import auto_generate_page_seo
            if not self.instance.seo_title or self.instance.seo_autogenerated:
                auto_generate_page_seo(self.instance, force=True)
                # Update form initial values
                self.initial['seo_title'] = self.instance.seo_title
                self.initial['seo_description'] = self.instance.seo_description
                self.initial['seo_keywords'] = self.instance.seo_keywords
    
    def clean_seo_title(self):
        """Validate SEO title length."""
        title = self.cleaned_data.get('seo_title')
        if title is None:
            title = ''
        title = title.strip()
        if title and len(title) > 60:
            raise forms.ValidationError("SEO title must be 60 characters or less.")
        return title
    
    def clean_seo_description(self):
        """Validate SEO description length."""
        description = self.cleaned_data.get('seo_description')
        if description is None:
            description = ''
        description = description.strip()
        if description and len(description) > 160:
            raise forms.ValidationError("SEO description must be 160 characters or less.")
        return description
    
    def save(self, commit=True):
        """Override save to handle SEO auto-generation and manual edit flag."""
        instance = super().save(commit=False)
        
        # Check if user manually edited SEO fields
        if self.cleaned_data.get('seo_title') or self.cleaned_data.get('seo_description') or self.cleaned_data.get('seo_keywords'):
            # User provided SEO data - mark as manually edited
            instance.seo_autogenerated = False
        else:
            # Auto-generate if empty
            from .seo_services import auto_generate_page_seo
            auto_generate_page_seo(instance, force=True)
        
        if commit:
            instance.save()
        return instance
    
    def clean_slug(self):
        """Validate slug format if provided."""
        slug = self.cleaned_data.get('slug')
        if slug is None:
            slug = ''
        slug = slug.strip()
        if slug and not slug.replace('-', '').replace('_', '').isalnum():
            raise forms.ValidationError("Slug can only contain letters, numbers, hyphens, and underscores.")
        return slug


class PageEditForm(PageCreateForm):
    """
    Form for editing an existing page.
    
    Same as PageCreateForm but with additional validation for existing pages.
    """
    
    def __init__(self, *args, **kwargs):
        # Get instance before calling super to determine page_type
        instance = kwargs.get('instance')
        if instance and instance.pk:
            # Set allowed_page_types to only the instance's page_type
            kwargs.setdefault('allowed_page_types', [instance.page_type])
        
        super().__init__(*args, **kwargs)
        
        # For existing pages, make page_type not required (it's locked)
        if self.instance and self.instance.pk:
            self.fields['page_type'].required = False
            # Set initial value from instance
            self.initial['page_type'] = self.instance.page_type
            
            # For existing pages, auto-generate SEO if not set
            from .seo_services import auto_generate_page_seo
            if not self.instance.seo_title or self.instance.seo_autogenerated:
                auto_generate_page_seo(self.instance, force=True)
                # Update form initial values
                self.initial['seo_title'] = self.instance.seo_title
                self.initial['seo_description'] = self.instance.seo_description
                self.initial['seo_keywords'] = self.instance.seo_keywords
    
    def clean_page_type(self):
        """Ensure page_type is set from instance if not provided."""
        page_type = self.cleaned_data.get('page_type')
        if not page_type and self.instance and self.instance.pk:
            # Use instance's page_type if not provided (for edit forms)
            return self.instance.page_type
        return page_type

