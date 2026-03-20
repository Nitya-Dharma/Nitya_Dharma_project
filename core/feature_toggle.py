"""
Feature toggle helper. Admin-controlled visibility for features (e.g. news feed).
"""
from django.core.cache import cache


def is_feature_enabled(feature_name):
    """
    Return True if the feature toggle exists and enabled=True; otherwise False.
    """
    if not feature_name or not isinstance(feature_name, str):
        return False
    cache_key = f"feature_toggle:{feature_name}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached is True
    try:
        from core.models import FeatureToggle
        toggle = FeatureToggle.objects.filter(name=feature_name).first()
        enabled = toggle.enabled if toggle else False
        cache.set(cache_key, enabled, 60)  # 1 min cache to avoid DB on every request
        return enabled
    except Exception:
        return False
