"""
Phase 12: In-memory metrics registry for request timing and slow-request counts.
Thread-safe; no database storage. Metrics reset on server restart.
"""
import threading

metrics_lock = threading.Lock()

metrics = {
    "request_count": 0,
    "slow_requests": 0,
    "total_response_time": 0.0,
}

SLOW_REQUEST_THRESHOLD_SECONDS = 1.0


def record_request(duration: float) -> None:
    """Record a request and its duration; count as slow if duration > 1 second."""
    with metrics_lock:
        metrics["request_count"] += 1
        metrics["total_response_time"] += duration
        if duration > SLOW_REQUEST_THRESHOLD_SECONDS:
            metrics["slow_requests"] += 1


def get_metrics() -> dict:
    """Return current metrics; avg_response_time computed dynamically."""
    with metrics_lock:
        count = metrics["request_count"]
        total = metrics["total_response_time"]
        avg = (total / count) if count > 0 else 0.0
        return {
            "request_count": count,
            "slow_requests": metrics["slow_requests"],
            "avg_response_time": round(avg, 4),
        }
