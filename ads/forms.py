"""
ModelForm for Advertisement with optional script_code length validation (max 20,000 chars).
Includes URL exclusion, dashboard visibility, role targeting, and per-slot image validation.
"""

from django import forms
from .models import Advertisement, Campaign, AdSet
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
            'campaign': forms.Select(attrs={'class': 'form-select'}),
            'ad_set': forms.Select(attrs={'class': 'form-select'}),
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

        # Optional Campaign → AdSet hierarchy (both remain optional).
        if 'campaign' in self.fields:
            self.fields['campaign'].required = False
            self.fields['campaign'].queryset = Campaign.objects.all().order_by('-created_at')
            self.fields['campaign'].empty_label = 'No campaign'
            self.fields['campaign'].help_text = 'Optional. Campaign → AdSet → Advertisement.'
        if 'ad_set' in self.fields:
            self.fields['ad_set'].required = False
            self.fields['ad_set'].queryset = AdSet.objects.select_related('campaign').order_by(
                '-created_at'
            )
            self.fields['ad_set'].empty_label = 'No ad set'
            self.fields['ad_set'].help_text = (
                'Optional. If set, must belong to the selected Campaign '
                '(or Campaign is filled from the AdSet).'
            )
            # When a campaign is posted/initial, constrain AdSet choices for operators.
            campaign_id = None
            if self.data.get('campaign'):
                try:
                    campaign_id = int(self.data.get('campaign'))
                except (TypeError, ValueError):
                    campaign_id = None
            elif self.initial.get('campaign'):
                campaign_id = getattr(self.initial.get('campaign'), 'pk', self.initial.get('campaign'))
            elif self.instance and getattr(self.instance, 'campaign_id', None):
                campaign_id = self.instance.campaign_id
            if campaign_id:
                self.fields['ad_set'].queryset = self.fields['ad_set'].queryset.filter(
                    campaign_id=campaign_id
                )

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
        campaign = cleaned.get('campaign')
        ad_set = cleaned.get('ad_set')
        if ad_set is not None:
            if campaign is None:
                # Align optional Advertisement.campaign with the AdSet's required Campaign.
                cleaned['campaign'] = ad_set.campaign
            elif ad_set.campaign_id != campaign.pk:
                raise forms.ValidationError(
                    'Selected Ad Set does not belong to the selected Campaign.'
                )

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


class CampaignForm(forms.ModelForm):
    ROLE_CHOICES = [
        ("anonymous", "Anonymous (Not Logged In)"),
        ("user", "User"),
        ("pandit", "Pandit"),
        ("admin", "Admin"),
    ]

    target_roles = forms.MultipleChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Campaign
        fields = [
            "name",
            "status",
            "priority",
            "start_date",
            "end_date",
            "daily_budget",
            "total_budget",
            "spent_amount",
            "target_roles",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "maxlength": 120}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.NumberInput(attrs={"class": "form-control", "min": "1", "step": "1"}),
            "start_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "end_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "daily_budget": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "total_budget": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "spent_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
        ]
        self.fields["end_date"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
        ]
        if self.instance and self.instance.target_roles:
            self.initial["target_roles"] = self.instance.target_roles

    def clean_target_roles(self):
        roles = self.cleaned_data.get("target_roles", [])
        return list(roles)

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Campaign end date must be after start date.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.target_roles:
            instance.target_roles = ["anonymous", "user"]
        if commit:
            instance.save()
        return instance


class AdSetForm(forms.ModelForm):
    """Super Admin form for AdSet (Campaign → AdSet). Configuration fields only."""

    class Meta:
        model = AdSet
        fields = [
            "name",
            "campaign",
            "is_active",
            "placements",
            "target_urls",
            "target_roles",
            "target_locations",
            "pricing_model",
            "cpm_rate",
            "max_impressions",
            "frequency_cap",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "maxlength": 255}),
            "campaign": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "placements": forms.Textarea(
                attrs={
                    "class": "form-control font-monospace",
                    "rows": 3,
                    "placeholder": 'JSON array, e.g. ["top", "sidebar"]',
                }
            ),
            "target_urls": forms.Textarea(
                attrs={
                    "class": "form-control font-monospace",
                    "rows": 3,
                    "placeholder": '["/home", "/search*"]',
                }
            ),
            "target_roles": forms.Textarea(
                attrs={
                    "class": "form-control font-monospace",
                    "rows": 2,
                    "placeholder": '["user", "pandit"]',
                }
            ),
            "target_locations": forms.Textarea(
                attrs={
                    "class": "form-control font-monospace",
                    "rows": 2,
                    "placeholder": '["hyderabad", "mumbai"]',
                }
            ),
            "pricing_model": forms.Select(attrs={"class": "form-select"}),
            "cpm_rate": forms.NumberInput(attrs={"class": "form-control", "step": "any", "min": "0"}),
            "max_impressions": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1"}),
            "frequency_cap": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = True
        self.fields["campaign"].required = True
        campaign_qs = Campaign.objects.all().order_by("-created_at")
        self.fields["campaign"].queryset = campaign_qs
        self.fields["campaign"].empty_label = (
            "Select campaign" if campaign_qs.exists() else "No campaigns — create one first"
        )
        for fname in (
            "placements",
            "target_urls",
            "target_roles",
            "target_locations",
            "cpm_rate",
            "max_impressions",
            "frequency_cap",
        ):
            self.fields[fname].required = False

    def _clean_json_list_field(self, value, field_label):
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            if not value.strip():
                return []
            import json

            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                raise forms.ValidationError(f"{field_label}: enter valid JSON array or leave empty.")
            if not isinstance(parsed, list):
                raise forms.ValidationError(f"{field_label}: must be a JSON array.")
            return parsed
        return []

    def clean_placements(self):
        return self._clean_json_list_field(self.cleaned_data.get("placements"), "Placements")

    def clean_target_urls(self):
        return self._clean_json_list_field(self.cleaned_data.get("target_urls"), "Target URLs")

    def clean_target_roles(self):
        return self._clean_json_list_field(self.cleaned_data.get("target_roles"), "Target roles")

    def clean_target_locations(self):
        return self._clean_json_list_field(
            self.cleaned_data.get("target_locations"), "Target locations"
        )
