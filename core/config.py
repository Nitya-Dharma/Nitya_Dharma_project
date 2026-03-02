"""
Safe config overlay: DB-backed values for dashboard-editable settings only.
Fallback to default (settings or literal) when DB missing/fails. Never raise.
Uses Django cache backend (TTL 60s); shared across workers when backend is Redis.
"""
from django.core.cache import cache

_CONFIG_TTL_SECONDS = 60


def get_config_value(key, default, cast_type=int):
    """
    Return runtime value for a config key: DB overlay if present, else default.
    Cached via Django cache for 60 seconds. Never raises; on any error returns default.
    Never caches or returns None.
    """
    cache_key = f"system_config:{key}"
    try:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        pass
    try:
        from core.models_config import SystemConfig
        row = SystemConfig.objects.filter(key=key).first()
        if row is None or row.value is None or row.value == '':
            resolved = default
        else:
            resolved = cast_type(row.value)
    except (ValueError, TypeError, Exception):
        resolved = default
    if resolved is not None:
        try:
            cache.set(cache_key, resolved, timeout=_CONFIG_TTL_SECONDS)
        except Exception:
            pass
    return resolved


def invalidate_config_cache(key=None):
    """
    Clears cached config value.
    If key provided, clears only that key.
    If key is None, no-op (do not clear entire cache).
    Must never raise exception.
    """
    try:
        if key is not None:
            cache.delete(f"system_config:{key}")
    except Exception:
        pass
