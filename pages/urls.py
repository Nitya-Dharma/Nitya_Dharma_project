"""
URL configuration for pages app.

Security:
- All URLs use public_id (UUIDv7) to prevent enumeration attacks
- Access control is enforced in views
"""
from django.urls import path
from . import views
from . import post_views
from . import views_page_review_advanced
from . import views_static
from . import dashboard_views

app_name = 'pages'

urlpatterns = [
    # Page creation
    path('create/', views.page_create, name='page_create'),
    
    # Public FAQ Page (must be before generic page_public_id pattern)
    path('faq/', views_static.public_faq, name='public_faq'),
    
    # Page detail (public view)
    path('<str:page_public_id>/', views.page_detail, name='page_detail'),
    
    # Page edit
    path('<slug:slug>/edit/', views.page_edit, name='page_edit'),
    
    # Page status management
    path('<str:page_public_id>/deactivate/', views.page_deactivate, name='page_deactivate'),
    path('<str:page_public_id>/activate/', views.page_activate, name='page_activate'),
    path('<str:page_public_id>/make-invisible/', views.page_make_invisible, name='page_make_invisible'),
    path('<str:page_public_id>/make-visible/', views.page_make_visible, name='page_make_visible'),
    
    # Page list
    path('', views.page_list, name='page_list'),
    
    # Gallery management
    path('<str:page_public_id>/gallery/upload/', views.upload_gallery_image, name='upload_gallery_image'),
    path('<str:page_public_id>/gallery/<str:image_public_id>/delete/', views.delete_gallery_image, name='delete_gallery_image'),
    path('<str:page_public_id>/gallery/<str:image_public_id>/toggle-visibility/', views.toggle_gallery_image_visibility, name='toggle_gallery_image_visibility'),
    
    # Post management
    path('<str:page_public_id>/posts/create/', post_views.create_post, name='create_post'),
    path('<str:page_public_id>/posts/<str:post_public_id>/pin/', post_views.toggle_post_pin, name='toggle_post_pin'),
    path('<str:page_public_id>/posts/<str:post_public_id>/hide/', post_views.hide_post, name='hide_post'),
    path('<str:page_public_id>/posts/<str:post_public_id>/delete/', post_views.delete_post, name='delete_post'),
    path('<str:page_public_id>/posts/<str:post_public_id>/', post_views.view_post, name='view_post'),
    
    # Review management
    path('<str:page_public_id>/reviews/submit/', views.submit_review, name='submit_review'),
    
    # Advanced Page Review System endpoints
    path('api/review/<int:review_id>/helpful/', views_page_review_advanced.vote_page_review_helpful, name='page_review_helpful'),
    path('api/review/<str:public_id>/report/', views_page_review_advanced.report_page_review_advanced, name='page_review_report'),
    
    # Moderator management
    path('<str:page_public_id>/moderators/', views.manage_moderators, name='manage_moderators'),
    path('<str:page_public_id>/moderators/search/', views.search_pandits, name='search_pandits'),
    path('<str:page_public_id>/moderators/assign/', views.assign_moderator, name='assign_moderator'),
    path('<str:page_public_id>/moderators/remove/', views.remove_moderator, name='remove_moderator'),
    
    # CMS Static Pages (must be before dynamic page routes)
    path('static/<slug:slug>/', views_static.static_page_detail, name='static_page_detail'),
    
    # Dashboard CMS Management (Super Admin only)
    # IMPORTANT: More specific routes must come before generic slug routes
    path('dashboard/super-admin/content/', dashboard_views.cms_list, name='super_admin_cms_list'),
    path('dashboard/super-admin/content/init-defaults/', dashboard_views.cms_init_defaults, name='super_admin_cms_init_defaults'),
    path('dashboard/super-admin/content/seo-config/', dashboard_views.cms_seo_config, name='super_admin_cms_seo_config'),
    path('dashboard/super-admin/content/<slug:slug>/revisions/', dashboard_views.cms_revisions, name='super_admin_cms_revisions'),
    path('dashboard/super-admin/content/<slug:slug>/', dashboard_views.cms_edit, name='super_admin_cms_edit'),
    
    # Social Media Settings (Super Admin only)
    path('dashboard/super-admin/social-links/', dashboard_views.cms_social_settings, name='super_admin_social_settings'),
    
    # FAQ Management (Super Admin only)
    path('dashboard/super-admin/faq/', dashboard_views.faq_list, name='super_admin_faq_list'),
    path('dashboard/super-admin/faq/create/', dashboard_views.faq_create, name='super_admin_faq_create'),
    path('dashboard/super-admin/faq/<int:pk>/edit/', dashboard_views.faq_edit, name='super_admin_faq_edit'),
    path('dashboard/super-admin/faq/<int:pk>/delete/', dashboard_views.faq_delete, name='super_admin_faq_delete'),
]
