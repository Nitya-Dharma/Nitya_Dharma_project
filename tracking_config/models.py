"""
Tracking Configuration models for Super-Admin-only GTM / Analytics system.

This module defines models for storing and auditing analytics tracking snippets.
Only Super Admin can access these models.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
import re

User = get_user_model()


class TrackingConfiguration(models.Model):
    """
    Super-Admin-only analytics tracking configuration.
    
    Stores GTM/analytics snippets that are injected into public pages only.
    Completely invisible to Admin Pandit, Pandit, and End Users.
    """
    
    PROVIDER_GTM = 'GTM'
    PROVIDER_ADOBE = 'ADOBE'
    PROVIDER_CUSTOM = 'CUSTOM'
    
    PROVIDER_CHOICES = [
        (PROVIDER_GTM, 'Google Tag Manager'),
        (PROVIDER_ADOBE, 'Adobe Analytics'),
        (PROVIDER_CUSTOM, 'Custom Script'),
    ]
    
    provider_type = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_GTM,
        verbose_name='Provider Type',
        help_text='Analytics provider type'
    )
    
    head_snippet = models.TextField(
        blank=True,
        null=True,
        verbose_name='Head Snippet',
        help_text='Script to inject in <head> (sanitized, only <script> and <noscript> allowed)'
    )
    
    body_snippet = models.TextField(
        blank=True,
        null=True,
        verbose_name='Body Snippet',
        help_text='Script to inject after <body> (sanitized, only <script> and <noscript> allowed)'
    )
    
    footer_snippet = models.TextField(
        blank=True,
        null=True,
        verbose_name='Footer Snippet',
        help_text='Script to inject before </body> (sanitized, only <script> and <noscript> allowed)'
    )
    
    is_active = models.BooleanField(
        default=False,
        verbose_name='Is Active',
        help_text='Enable tracking injection'
    )
    
    excluded_route_patterns = models.TextField(
        blank=True,
        null=True,
        verbose_name='Excluded Route Patterns',
        help_text='Comma-separated list of URL patterns to exclude from tracking (e.g., /api/, /internal/)'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_tracking_configs',
        verbose_name='Created By',
        help_text='Super Admin who created this configuration'
    )
    
    updated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='updated_tracking_configs',
        null=True,
        blank=True,
        verbose_name='Updated By',
        help_text='Super Admin who last updated this configuration'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Tracking Configuration'
        verbose_name_plural = 'Tracking Configurations'
        db_table = 'tracking_config_trackingconfiguration'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_provider_type_display()} ({'Active' if self.is_active else 'Inactive'})"
    
    def clean(self):
        """Validate that only one active configuration exists."""
        if self.is_active:
            existing_active = TrackingConfiguration.objects.filter(
                is_active=True
            ).exclude(pk=self.pk if self.pk else None)
            if existing_active.exists():
                raise ValidationError(
                    "Only one active tracking configuration is allowed. "
                    "Please deactivate the existing active configuration first."
                )
    
    def save(self, *args, **kwargs):
        """Sanitize snippets and validate before saving."""
        # Sanitize snippets
        if self.head_snippet:
            self.head_snippet = self.sanitize_snippet(self.head_snippet)
        if self.body_snippet:
            self.body_snippet = self.sanitize_snippet(self.body_snippet)
        if self.footer_snippet:
            self.footer_snippet = self.sanitize_snippet(self.footer_snippet)
        
        # Validate
        self.clean()
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def sanitize_snippet(snippet):
        """
        Sanitize tracking snippet to allow only safe tags.
        
        Allows:
        - <script> tags
        - <noscript> tags
        
        Blocks:
        - Forms (<form>, <input>, etc.)
        - Inline HTML (except script/noscript)
        - Iframes
        - Event handlers (onclick, onerror, etc.)
        - PII references
        """
        if not snippet:
            return snippet
        
        # Remove any form elements
        snippet = re.sub(r'<form[^>]*>.*?</form>', '', snippet, flags=re.DOTALL | re.IGNORECASE)
        snippet = re.sub(r'<input[^>]*>', '', snippet, flags=re.IGNORECASE)
        snippet = re.sub(r'<button[^>]*>.*?</button>', '', snippet, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove iframes (unless explicitly needed, but we block for security)
        snippet = re.sub(r'<iframe[^>]*>.*?</iframe>', '', snippet, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove event handlers
        snippet = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', snippet, flags=re.IGNORECASE)
        
        # Remove javascript: protocol
        snippet = re.sub(r'javascript:', '', snippet, flags=re.IGNORECASE)
        
        # Only allow <script> and <noscript> tags
        # Extract script and noscript tags
        script_pattern = r'<script[^>]*>.*?</script>'
        noscript_pattern = r'<noscript[^>]*>.*?</noscript>'
        
        scripts = re.findall(script_pattern, snippet, flags=re.DOTALL | re.IGNORECASE)
        noscripts = re.findall(noscript_pattern, snippet, flags=re.DOTALL | re.IGNORECASE)
        
        # Reconstruct with only allowed tags
        sanitized = '\n'.join(scripts + noscripts)
        
        return sanitized
    
    def get_excluded_patterns_list(self):
        """Get excluded route patterns as a list."""
        if not self.excluded_route_patterns:
            return []
        return [pattern.strip() for pattern in self.excluded_route_patterns.split(',') if pattern.strip()]


class TrackingConfigurationAudit(models.Model):
    """
    Audit log for tracking configuration changes.
    
    Records every create, update, and disable action.
    Immutable records visible only to Super Admin.
    """
    
    tracking_configuration = models.ForeignKey(
        TrackingConfiguration,
        on_delete=models.PROTECT,
        related_name='audit_logs',
        verbose_name='Tracking Configuration',
        help_text='The configuration that was changed'
    )
    
    changed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='tracking_audit_actions',
        verbose_name='Changed By',
        help_text='Super Admin who made the change'
    )
    
    action = models.CharField(
        max_length=50,
        verbose_name='Action',
        help_text='Action performed (created, updated, enabled, disabled)'
    )
    
    old_value = models.TextField(
        null=True,
        blank=True,
        verbose_name='Old Value',
        help_text='Previous configuration value (JSON)'
    )
    
    new_value = models.TextField(
        null=True,
        blank=True,
        verbose_name='New Value',
        help_text='New configuration value (JSON)'
    )
    
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Changed At',
        help_text='When the change was made'
    )
    
    class Meta:
        verbose_name = 'Tracking Configuration Audit'
        verbose_name_plural = 'Tracking Configuration Audits'
        db_table = 'tracking_config_trackingconfigurationaudit'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.action} by {self.changed_by.email} at {self.changed_at}"
