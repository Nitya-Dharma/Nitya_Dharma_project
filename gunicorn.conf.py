"""
Gunicorn configuration for production deployment.
Used by Railway, Render, Fly.io, etc. PORT is provided by the platform.
"""
import os

bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
workers = 3
timeout = 120

# Platform/Procfile path: default to production settings when unset.
# Explicit DJANGO_SETTINGS_MODULE (including .dev) is preserved via setdefault.
# Mirrors gunicorn_config.py (Hostinger) — do not change that primary path here.
def on_starting(server):
    if os.environ.get("DJANGO_SETTINGS_MODULE") != "nityadharma.settings.prod":
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nityadharma.settings.prod")
