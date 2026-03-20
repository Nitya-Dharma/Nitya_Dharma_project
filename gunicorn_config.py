"""
Gunicorn configuration for Hostinger KVM2 VPS (2 vCPU, 8GB RAM).
Use with: gunicorn nityadharma.wsgi:application --config gunicorn_config.py
Set DJANGO_SETTINGS_MODULE=nityadharma.settings.prod when running.
"""
import os

# Bind to localhost; Nginx reverse proxy forwards to this port
bind = "127.0.0.1:8000"

# 2 vCPU: 2–4 workers. Use 3 for a balance of throughput and memory (8GB RAM)
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Allow long-running requests (e.g. exports, uploads)
timeout = 120
graceful_timeout = 30
keepalive = 2

# Process naming
proc_name = "nityadharma"

# Logging (stdout/stderr for systemd to capture)
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Ensure production settings
def on_starting(server):
    if os.environ.get("DJANGO_SETTINGS_MODULE") != "nityadharma.settings.prod":
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nityadharma.settings.prod")
