"""
Phase 12: Runtime system information. Read-only diagnostics.
"""
import multiprocessing
import os
import platform
import sys


def get_system_info() -> dict:
    """Return Python version, Django version, OS, CPU count; optionally memory if psutil available."""
    info = {
        "python_version": sys.version.split()[0],
        "django_version": "",
        "platform": platform.system(),
        "platform_release": platform.release(),
        "cpu_count": multiprocessing.cpu_count(),
    }
    try:
        import django
        info["django_version"] = django.get_version()
    except Exception:
        pass
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        info["memory_mb"] = round(proc.memory_info().rss / (1024 * 1024), 2)
    except ImportError:
        pass
    return info
