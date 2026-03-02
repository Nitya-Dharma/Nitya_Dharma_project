"""
DB-backed configuration overlay for dashboard-editable operational settings only.
Stores only the 6 allowed keys; fallback to settings when missing.
"""
from django.conf import settings
from django.db import models


# Only these keys may be stored and edited via Super Admin dashboard.
ALLOWED_CONFIG_KEYS = frozenset({
    'CONTACT_RATE_LIMIT_COUNT',
    'CONTACT_RATE_LIMIT_WINDOW_SECONDS',
    'REFERRAL_HIGH_TIER_100_ALERT_THRESHOLD',
    'REFERRAL_HIGH_TIER_50_ALERT_THRESHOLD',
    'DASHBOARD_PAGES_PREVIEW_LIMIT',
    'DASHBOARD_AUDIT_EXPORT_LIMIT',
})


class SystemConfig(models.Model):
    """
    Key-value store for Super Admin–editable operational settings.
    Only allowed keys (ALLOWED_CONFIG_KEYS) should be written via dashboard.
    If key missing → consumers fall back to settings/default.
    """
    key = models.CharField(
        max_length=120,
        unique=True,
        db_index=True,
        verbose_name='Config Key',
        help_text='Setting key (e.g. CONTACT_RATE_LIMIT_COUNT). Only allowed keys are editable via dashboard.',
    )
    value = models.CharField(
        max_length=255,
        verbose_name='Value',
        help_text='Stored value (string); consumers cast to int.',
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='system_config_changes',
        verbose_name='Updated By',
    )

    class Meta:
        db_table = 'core_systemconfig'
        verbose_name = 'System Config'
        verbose_name_plural = 'System Configs'
        ordering = ['key']

    def __str__(self):
        return f'{self.key}={self.value}'
