"""
Phase 12: Structured logging configuration for the monitoring module.
Extends logging safely; does not override existing project logging.
"""
import logging

# Format: timestamp, level, module, message
MONITORING_FORMAT = "[%(asctime)s] %(levelname)s %(name)s %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def configure_monitoring_logging() -> None:
    """
    Configure loggers for monitoring, django.request, django.db.backends.
    Safe to call; only adds handlers/formats for these loggers if not already set.
    """
    for name in ("monitoring", "monitoring.middleware", "monitoring.slow_query_detector"):
        log = logging.getLogger(name)
        if not log.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(MONITORING_FORMAT, datefmt=DATE_FMT))
            log.addHandler(handler)
            log.setLevel(logging.INFO)
