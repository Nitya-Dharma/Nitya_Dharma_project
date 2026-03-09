"""
URL configuration for profiles app.

Security:
- All URLs use unique profile IDs (pk) to prevent enumeration attacks
- Profile IDs are auto-incrementing BigAutoField (unique by design)
- Access control is enforced in views, not URLs
"""
from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    # IMPORTANT: Specific paths must come BEFORE generic patterns
    # Otherwise Django will match "edit" and "private" as public_id values
    
    # Profile edit - uses public_id for security
    # Security: Only profile owner can edit
    path('edit/', views.profile_edit, name='profile_edit'),
    path('edit/<str:public_id>/', views.profile_edit, name='profile_edit_with_id'),
    
    # Private profile view - uses public_id
    # Security: Only profile owner can view
    path('private/', views.profile_private, name='profile_private'),
    path('private/<str:public_id>/', views.profile_private, name='profile_private_with_id'),
    
    # Public profile view - supports both slug and public_id (Phase 11B.1 / 11B.2)
    # Security: Only approved profiles are accessible
    # id/<public_id>/ for explicit public_id (templates using public_id=)
    path('id/<str:public_id>/', views.profile_public, name='profile_public_by_id'),
    # <slug:identifier>/ for SEO slug or public_id (letters, numbers, hyphens, underscores only)
    path('<slug:identifier>/', views.profile_public, name='profile_public'),
]




