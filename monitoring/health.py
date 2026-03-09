"""
Phase 12: System health checks. Read-only; never raises; never modifies data.
"""
import logging
import shutil
import time
from django.conf import settings
from django.core.cache import cache
from django.db import connection

logger = logging.getLogger("monitoring.health")

_process_start_time = time.time()
MIN_FREE_DISK_BYTES = 100 * 1024 * 1024  # 100 MB


def check_database() -> str:
    """Execute SELECT 1; return 'ok' or 'error'. Does not raise."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return "ok"
    except Exception as e:
        logger.debug("health check database: %s", e)
        return "error"


def check_cache() -> str:
    """Set and retrieve a temporary key; return 'ok' or 'error'. Does not raise."""
    try:
        key = "monitoring_test_key"
        cache.set(key, 1, timeout=5)
        cache.get(key)
        return "ok"
    except Exception as e:
        logger.debug("health check cache: %s", e)
        return "error"


def check_disk() -> str:
    """Check free disk space; return 'ok' if free > 100MB. Does not raise."""
    try:
        import os
        path = os.path.expanduser("~") or os.path.abspath(".")
        usage = shutil.disk_usage(path)
        return "ok" if usage.free > MIN_FREE_DISK_BYTES else "error"
    except Exception as e:
        logger.debug("health check disk: %s", e)
        return "error"


def get_uptime() -> float:
    """Return process uptime in seconds."""
    return time.time() - _process_start_time


def get_health_status() -> dict:
    """
    Return health status dict. Never raises; all checks wrapped in try/except.
    status is 'healthy' if all ok, else 'degraded'.
    """
    db = check_database()
    cache_status = check_cache()
    disk = check_disk()
    uptime = get_uptime()
    status = "healthy" if (db == "ok" and cache_status == "ok" and disk == "ok") else "degraded"
    return {
        "status": status,
        "database": db,
        "cache": cache_status,
        "disk": disk,
        "uptime_seconds": round(uptime, 2),
    }
