# Pytest configuration for Django project (Phase 9.5)
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nityadharma.settings.dev')
django.setup()
