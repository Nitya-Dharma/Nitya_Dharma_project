"""
URL configuration for reviews app.

Tasks:
- 9.3: Review Submission Eligibility & Validation
- 9.4: Review Visibility & Access Rules

Backend APIs and UI views for review operations.
"""

from django.urls import path
from . import views
from . import views_ui
from . import views_advanced
from . import views_moderation

app_name = 'reviews'

urlpatterns = [
    # API endpoints (JSON)
    path('api/create/', views.create_review, name='create_review'),
    path('api/my-reviews/', views.list_my_reviews, name='list_my_reviews'),
    path('api/pandit/<str:pandit_public_id>/', views.list_reviews_for_pandit, name='list_reviews_for_pandit_api'),
    path('api/<str:public_id>/', views.get_review, name='get_review'),
    path('api/pandit/<str:pandit_public_id>/ratings/', views.get_rating_aggregation, name='get_rating_aggregation'),
    path('api/<str:public_id>/report/', views.report_review, name='report_review'),
    path('api/governance/', views.list_all_for_governance, name='list_all_for_governance'),
    path('api/<str:public_id>/change-visibility/', views.change_visibility, name='change_visibility'),
    
    # Advanced Review System endpoints
    path('api/review/<int:review_id>/helpful/', views_advanced.vote_helpful, name='review_helpful'),
    path('api/<str:public_id>/report-advanced/', views_advanced.report_review_advanced, name='report_review_advanced'),
    
    # UI endpoints (HTML templates)
    path('pandit/<str:pandit_public_id>/', views_ui.pandit_reviews, name='pandit_reviews'),
    path('pandit/<str:pandit_public_id>/submit/', views_ui.submit_review, name='submit_review'),
    
    # Moderation dashboard (Admin only)
    path('admin/moderation/', views_moderation.moderation_dashboard, name='moderation_dashboard'),
    path('admin/moderate/<int:review_id>/', views_moderation.moderate_review, name='moderate_review'),
]

