"""
Phase 12: Request timing middleware. Observational only; does not alter responses.
"""
import logging
import time

from .metrics import record_request
from .slow_query_detector import inspect_slow_queries

logger = logging.getLogger("monitoring.middleware")

SLOW_WARNING_SECONDS = 1.0
SLOW_ERROR_SECONDS = 3.0


class RequestTimingMiddleware:
    """Measure request processing time; log slow requests; update metrics. Does not alter response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start_time

        record_request(duration)
        inspect_slow_queries()

        method = getattr(request, "method", "?")
        path = getattr(request, "path", "?")
        status = getattr(response, "status_code", 0)

        if duration >= SLOW_ERROR_SECONDS:
            logger.error(
                "[SLOW REQUEST] method=%s path=%s duration=%.2fs status=%s",
                method,
                path,
                duration,
                status,
            )
        elif duration >= SLOW_WARNING_SECONDS:
            logger.warning(
                "[SLOW REQUEST] method=%s path=%s duration=%.2fs status=%s",
                method,
                path,
                duration,
                status,
            )

        return response
