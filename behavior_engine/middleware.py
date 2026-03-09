"""
Phase 14: Page view tracking middleware. GET only; ignores admin, monitoring, static.
"""
from .trackers import track_page_view


class PageViewTrackingMiddleware:
    """Record page views for GET requests. Ignores admin, monitoring, static. Never blocks or raises."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if request.method != "GET":
                return response
            path = (request.path or "").strip()
            if not path:
                return response
            if path.startswith("/admin/"):
                return response
            if path.startswith("/monitoring/"):
                return response
            if path.startswith("/static/") or path.startswith("/media/"):
                return response
            track_page_view(request, path=path)
        except Exception:
            pass
        return response
