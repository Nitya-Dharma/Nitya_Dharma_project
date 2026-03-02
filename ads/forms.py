"""
ModelForm for Advertisement with optional script_code length validation (max 20,000 chars).
Includes URL exclusion, dashboard visibility, and role targeting.
"""

from django import forms
from .models import Advertisement

SCRIPT_CODE_MAX_LENGTH = 20_000


class AdvertisementForm(forms.ModelForm):
    class Meta:
        model = Advertisement
        fields = "__all__"
        exclude = ['placement']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100}),
            'ad_type': forms.Select(attrs={'class': 'form-select'}),
            'script_code': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 12}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control'}, format='%Y-%m-%dT%H:%M'),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'redirect_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'banner_width': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'e.g. 970'}),
            'banner_height': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'e.g. 90'}),
            'is_responsive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mobile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'exclude_urls': forms.Textarea(
                attrs={
                    'class': 'form-control font-monospace',
                    'rows': 4,
                    'placeholder': 'One URL prefix per line, e.g.:\n/login/\n/register/',
                }
            ),
            'show_on_dashboard': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'target_roles': forms.Textarea(
                attrs={
                    'class': 'form-control font-monospace',
                    'rows': 2,
                    'placeholder': '["user", "pandit"] or leave empty for all',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Multi-slot checkboxes (replaces single placement dropdown)
        self.fields['slots'] = forms.MultipleChoiceField(
            choices=Advertisement.PLACEMENT_CHOICES,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            required=True,
            label='Positions',
            help_text='Select one or more positions where this ad should appear.',
        )
        if self.instance and self.instance.pk:
            self.fields['slots'].initial = (
                self.instance.slots
                if (getattr(self.instance, 'slots', None) and len(self.instance.slots))
                else ([self.instance.placement] if getattr(self.instance, 'placement', None) else [])
            )
        self.fields['start_date'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d']
        self.fields['end_date'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d']

    def clean_target_roles(self):
        value = self.cleaned_data.get('target_roles')
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            if not value.strip():
                return []
            import json
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (ValueError, TypeError):
                return []
        return []

    def clean_script_code(self):
        value = self.cleaned_data.get('script_code') or ''
        if len(value) > SCRIPT_CODE_MAX_LENGTH:
            raise forms.ValidationError(
                f'Script code must be at most {SCRIPT_CODE_MAX_LENGTH:,} characters.'
            )
        return value
