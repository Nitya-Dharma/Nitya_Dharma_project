"""
Forms for Branding Logo Management
"""
from django import forms
from .models import BrandingLogo


class BrandingLogoUploadForm(forms.ModelForm):
    """Form for uploading new branding logos."""
    
    class Meta:
        model = BrandingLogo
        fields = ['name', 'logo_type', 'logo_image', 'favicon_image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Main Logo 2024, Dark Mode Logo',
            }),
            'logo_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'logo_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/png,image/svg+xml,image/webp,image/jpeg,image/jpg',
            }),
            'favicon_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/png,image/x-icon,image/jpeg',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = False
        self.fields['logo_type'].required = True
        self.fields['logo_image'].required = True
        self.fields['favicon_image'].required = False
        
        # Add help text
        self.fields['name'].help_text = 'Optional: Descriptive name for this logo'
        self.fields['logo_image'].help_text = 'PNG, SVG, or WEBP (max 500KB, 100-800px width)'
        self.fields['favicon_image'].help_text = 'Optional: PNG or ICO (max 50KB, 16x16 or 32x32 recommended)'

