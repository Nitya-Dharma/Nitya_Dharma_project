"""
Phase 12: Read-only inspection of slow database queries.
Uses connection.queries only when DEBUG=True. Never modifies queries or execution.
"""
import logging
from django.conf import settings
from django.db import connection

logger = logging.getLogger("monitoring.slow_query_detector")

SLOW_QUERY_THRESHOLD_SECONDS = 0.5


def inspect_slow_queries() -> None:
    """
    If DEBUG is True, inspect connection.queries and log any taking > 0.5s.
    Read-only; never modifies query execution.
    """
    if not getattr(settings, "DEBUG", False):
        return
    if not hasattr(connection, "queries"):
        return
    for q in connection.queries:
        try:
            t = float(q.get("time", 0))
        except (TypeError, ValueError):
            continue
        if t >= SLOW_QUERY_THRESHOLD_SECONDS:
            sql = q.get("sql", "")[:500]
            # The behavior tracking endpoints can write frequently in normal UX
            # (scroll_depth/page_view). Suppress slow-query warnings for those
            # writes to reduce log noise while keeping detection for everything else.
            sql_compact = sql.replace("\n", " ").strip()
            if sql_compact.startswith("INSERT INTO `behavior_event_log`"):
                continue
            logger.warning(
                "[SLOW QUERY] time=%.2fs sql=%s",
                t,
                sql_compact,
            )
