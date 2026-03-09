"""
Phase 12: Monitoring endpoints. Read-only; always return JSON; never raise to caller.
"""
from django.http import JsonResponse

from .health import get_health_status, get_uptime
from .metrics import get_metrics
from .system_info import get_system_info


def _format_uptime(seconds: float) -> str:
    """Format uptime seconds as e.g. '3h 12m'."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m = s // 60
    s = s % 60
    if m < 60:
        return f"{m}m {s}s" if s else f"{m}m"
    h = m // 60
    m = m % 60
    return f"{h}h {m}m" if m else f"{h}h"


def system_health_view(request):
    """GET /monitoring/health/ — health status and basic metrics. Never raises."""
    try:
        health = get_health_status()
        metrics = get_metrics()
        payload = {
            "status": health["status"],
            "database": health["database"],
            "cache": health["cache"],
            "disk": health["disk"],
            "uptime": _format_uptime(health["uptime_seconds"]),
            "requests_processed": metrics["request_count"],
            "slow_requests": metrics["slow_requests"],
        }
        return JsonResponse(payload)
    except Exception:
        return JsonResponse(
            {"status": "error", "message": "Health check failed"},
            status=500,
        )


def metrics_view(request):
    """GET /monitoring/metrics/ — request count, slow count, avg response time; optional system info."""
    try:
        payload = get_metrics()
        payload["system"] = get_system_info()
        return JsonResponse(payload)
    except Exception:
        return JsonResponse(
            {"error": "Metrics unavailable"},
            status=500,
        )
