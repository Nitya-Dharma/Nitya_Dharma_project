"""
Forms for Super Admin Dashboard.
"""
from django import forms
from pages.models import Page
from pages.constants import PAGE_STATUS_CHOICES
from masterdata.models import City, LocalArea, Pooja, Language, PoojaCategory


class PageEditFormSuperAdmin(forms.ModelForm):
    """
    Form for Super Admin to edit any page.
    Allows editing of core fields and visibility status.
    """
    status = forms.ChoiceField(
        choices=PAGE_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
        help_text='Visibility status of the page (ACTIVE, DEACTIVATED, INVISIBLE)'
    )

    class Meta:
        model = Page
        fields = ['title', 'description', 'address', 'city', 'area', 'profile_image', 'cover_image',
                  'seo_title', 'seo_description', 'seo_keywords', 'status']
        widgets = {
            'title': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
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
        super().__init__(*args, **kwargs)
        # Make all fields required=False by default, as Super Admin can partially update
        for field_name, field in self.fields.items():
            field.required = False
        
        # Except status, which is explicitly handled
        self.fields['status'].required = True
        
        # Populate city and area choices
        from masterdata.models import City, LocalArea
        self.fields['city'].queryset = City.objects.all().order_by('name')
        self.fields['area'].queryset = LocalArea.objects.all().order_by('name')
        self.fields['city'].empty_label = 'Select City'
        self.fields['area'].empty_label = 'Select Area'


# ============================================================================
# UNIT 20: Master Data Management Forms
# ============================================================================

class CityForm(forms.ModelForm):
    """Form for creating/editing City master data."""
    class Meta:
        model = City
        fields = ['name', 'state', 'is_active', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class LocalAreaForm(forms.ModelForm):
    """Form for creating/editing LocalArea master data."""
    class Meta:
        model = LocalArea
        fields = ['name', 'city', 'is_active', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].queryset = City.objects.filter(is_active=True).order_by('name')
        self.fields['city'].empty_label = 'Select City'


class PoojaForm(forms.ModelForm):
    """Form for creating/editing Pooja master data."""
    class Meta:
        model = Pooja
        fields = ['name', 'pooja_category', 'category', 'description', 'is_active', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'pooja_category': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pooja_category'].queryset = PoojaCategory.objects.filter(is_active=True).order_by('display_order', 'name')
        self.fields['pooja_category'].empty_label = 'Select Category'
        self.fields['category'].required = False  # Deprecated field


class LanguageForm(forms.ModelForm):
    """Form for creating/editing Language master data."""
    class Meta:
        model = Language
        fields = ['code', 'name', 'native_name', 'is_active', 'status']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '10'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'native_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class PoojaCategoryForm(forms.ModelForm):
    """Form for creating/editing PoojaCategory master data."""
    class Meta:
        model = PoojaCategory
        fields = ['name', 'description', 'display_order', 'is_active', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
