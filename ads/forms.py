"""
ModelForm for Advertisement with optional script_code length validation (max 20,000 chars).
Includes URL exclusion, dashboard visibility, role targeting, and per-slot image validation.
"""

from django import forms
from .models import Advertisement
from .constants import AD_POSITION_IMAGE_SIZES, AD_POSITION_LABELS

SCRIPT_CODE_MAX_LENGTH = 20_000


def _has_image(field_value, instance, field_name):
    """True if field has an uploaded file or instance has existing file."""
    if field_value and hasattr(field_value, 'name') and field_value.name:
        return True
    if instance and instance.pk:
        try:
            f = getattr(instance, field_name, None)
            return f and getattr(f, 'name', None)
        except (ValueError, AttributeError):
            pass
    return False


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
            'image': forms.FileInput(attrs={'class': 'form-control ad-slot-upload', 'data-slot': 'legacy'}),
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
            'image_top': forms.FileInput(attrs={'class': 'form-control ad-slot-upload', 'data-slot': 'top', 'accept': 'image/*'}),
            'image_sidebar': forms.FileInput(attrs={'class': 'form-control ad-slot-upload', 'data-slot': 'sidebar', 'accept': 'image/*'}),
            'image_footer': forms.FileInput(attrs={'class': 'form-control ad-slot-upload', 'data-slot': 'footer', 'accept': 'image/*'}),
            'image_in_content': forms.FileInput(attrs={'class': 'form-control ad-slot-upload', 'data-slot': 'in_content', 'accept': 'image/*'}),
            'image_dashboard_top': forms.FileInput(attrs={'class': 'form-control ad-slot-upload', 'data-slot': 'dashboard_top', 'accept': 'image/*'}),
            'image_dashboard_sidebar': forms.FileInput(attrs={'class': 'form-control ad-slot-upload', 'data-slot': 'dashboard_sidebar', 'accept': 'image/*'}),
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

    def clean(self):
        cleaned = super().clean()
        ad_type = cleaned.get('ad_type')
        slots = list(cleaned.get('slots') or [])
        if ad_type != Advertisement.AD_TYPE_IMAGE or not slots:
            return cleaned
        # Legacy: one image for all
        legacy_has = _has_image(cleaned.get('image'), self.instance, 'image')
        # Per-slot: require each selected slot to have an image (or legacy covers all)
        for slot in slots:
            field_name = Advertisement.SLOT_IMAGE_FIELDS.get(slot)
            if not field_name:
                continue
            slot_has = _has_image(cleaned.get(field_name), self.instance, field_name)
            if not slot_has and not legacy_has:
                label = AD_POSITION_LABELS.get(slot, slot)
                raise forms.ValidationError(
                    f'Please upload an image for the selected position "{label}", or use the single "Image" upload to cover all positions.'
                )
        # Dimension validation for uploaded per-slot images (warn only; recommend correct size)
        for slot, field_name in Advertisement.SLOT_IMAGE_FIELDS.items():
            uploaded = cleaned.get(field_name)
            if not uploaded or not getattr(uploaded, 'name', None):
                continue
            size_info = AD_POSITION_IMAGE_SIZES.get(slot)
            if not size_info:
                continue
            try:
                from PIL import Image as PILImage
                if hasattr(uploaded, 'seek'):
                    uploaded.seek(0)
                img = PILImage.open(uploaded)
                w, h = img.size
                img.close()
                rec_w, rec_h = size_info['width'], size_info['height']
                if w < rec_w or h < rec_h:
                    label = AD_POSITION_LABELS.get(slot, slot)
                    raise forms.ValidationError(
                        {field_name: f'Recommended size for {label} is {rec_w}×{rec_h}px. Uploaded image is {w}×{h}px. Please use an image of at least {rec_w}×{rec_h} for best display.'}
                    )
            except (OSError, TypeError, AttributeError):
                pass
        return cleaned
