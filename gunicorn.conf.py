"""
Gunicorn configuration for production deployment.
Used by Railway, Render, Fly.io, etc. PORT is provided by the platform.
"""
import os

bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
workers = 3
timeout = 120
