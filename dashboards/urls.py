"""
URL configuration for dashboards app.
"""
from django.urls import path
from . import views
from . import views_super_admin_intelligence

app_name = 'module5_dashboards'

urlpatterns = [
    path('user/', views.dashboard_user, name='dashboard_user'),
    path("expert/", views.expert_dashboard_view, name="expert_dashboard"),
    path('pandit/', views.dashboard_pandit, name='dashboard_pandit'),
    path('admin-pandit/', views.dashboard_admin_pandit, name='dashboard_admin_pandit'),
    path('super-admin/', views.dashboard_super_admin, name='dashboard_super_admin'),
    path("super-admin/experts/", views.super_admin_experts, name="super_admin_experts"),
    path(
        "super-admin/experts/bulk-approve/",
        views.bulk_approve_experts,
        name="bulk_approve_experts",
    ),
    path('super-admin/intelligence/', views_super_admin_intelligence.intelligence_dashboard, name='super_admin_intelligence'),
    # UNIT 8: Pandit Approval & Rejection (Super Admin only)
    path('super-admin/pandit/<int:user_id>/approve/', views.approve_pandit_super_admin, name='approve_pandit_super_admin'),
    path('super-admin/pandit/<int:user_id>/reject/', views.reject_pandit_super_admin, name='reject_pandit_super_admin'),
    # UNIT 9: Pandit Suspension & Reinstatement (Super Admin only)
    path('super-admin/pandit/<int:user_id>/suspend/', views.suspend_pandit_super_admin, name='suspend_pandit_super_admin'),
    path('super-admin/pandit/<int:user_id>/reinstate/', views.reinstate_pandit_super_admin, name='reinstate_pandit_super_admin'),
    # UNIT 15: SEO Metadata Oversight (Super Admin only)
    path('super-admin/seo/reset/<str:entity_type>/<str:entity_public_id>/', views.reset_seo_super_admin, name='reset_seo_super_admin'),
    path('super-admin/seo/edit/<str:entity_type>/<str:entity_public_id>/', views.edit_seo_super_admin, name='edit_seo_super_admin'),
    # UNIT 16: Indexing & Crawl Readiness Monitor (Super Admin only)
    path('super-admin/crawl-readiness/', views.crawl_readiness_monitor, name='crawl_readiness_monitor'),
    # UNIT 17: Analytics / GTM Configuration (Super Admin only)
    path('super-admin/analytics-config/', views.analytics_config_super_admin, name='analytics_config_super_admin'),
    # UNIT 18: Feature Flags (Super Admin only)
    path('super-admin/feature-flags/', views.feature_flags_super_admin, name='feature_flags_super_admin'),
    # System Operational Settings (Super Admin only; 6 dashboard-editable config keys)
    path('super-admin/system-operational-settings/', views.system_operational_settings_super_admin, name='system_operational_settings_super_admin'),
    # UNIT 19: Platform Kill Switch (Super Admin only)
    path('super-admin/kill-switch/', views.platform_kill_switch_super_admin, name='platform_kill_switch_super_admin'),
    # UNIT 20: Configuration Change Audit (Super Admin only)
    path('super-admin/config-audit/', views.config_change_audit_super_admin, name='config_change_audit_super_admin'),
    # UNIT 20: Master Data Management (Super Admin only)
    path('super-admin/master-data/', views.master_data_management, name='master_data_management'),
    path('super-admin/master-data/<str:entity_type>/<int:entity_id>/edit/', views.master_data_edit, name='master_data_edit'),
    path('super-admin/master-data/<str:entity_type>/<int:entity_id>/toggle/', views.master_data_toggle_status, name='master_data_toggle_status'),
    # PART 4: Notifications, Exports & Safety Rails
    # UNIT 21: Notifications & Alerts (Super Admin only)
    path('super-admin/notifications/', views.super_admin_notifications, name='super_admin_notifications'),
    # Referral Management (Super Admin) - reuses referrals.services
    path('super-admin/referrals/', views.super_admin_referral_links, name='super_admin_referral_links'),
    path('super-admin/referrals/create/', views.super_admin_create_referral_link, name='super_admin_create_referral_link'),
    path('super-admin/referrals/<int:referral_link_id>/revoke/', views.super_admin_revoke_referral_link, name='super_admin_revoke_referral_link'),
    # UNIT 22: Data Export (Super Admin only)
    path('super-admin/export/', views.export_data_super_admin, name='export_data_super_admin'),
    # UNIT 24: Consistency Checks (Super Admin only)
    path('super-admin/consistency-checks/', views.consistency_checks_super_admin, name='consistency_checks_super_admin'),
    # UNIT 12: Page Edit & Override (Super Admin only)
    path('super-admin/page/<str:page_public_id>/edit/', views.edit_page_super_admin, name='edit_page_super_admin'),
    # UNIT 13: Page Disable / Restore (Super Admin only)
    path('super-admin/page/<str:page_public_id>/disable/', views.disable_page_super_admin, name='disable_page_super_admin'),
    path('super-admin/page/<str:page_public_id>/restore/', views.restore_page_super_admin, name='restore_page_super_admin'),
    # UNIT 15: SEO Metadata Oversight (Super Admin only)
    path('super-admin/seo/reset/pandit/<str:public_id>/', views.reset_pandit_seo_super_admin, name='reset_pandit_seo_super_admin'),
    path('super-admin/seo/reset/page/<str:public_id>/', views.reset_page_seo_super_admin, name='reset_page_seo_super_admin'),
    path('super-admin/seo/edit/pandit/<str:public_id>/', views.edit_pandit_seo_super_admin, name='edit_pandit_seo_super_admin'),
    path('super-admin/seo/edit/page/<str:public_id>/', views.edit_page_seo_super_admin, name='edit_page_seo_super_admin'),
    # Pandit onboarding actions (Admin Pandit only - UI versions)
    path('admin-pandit/pandit/<int:user_id>/approve/', views.approve_pandit_ui, name='approve_pandit_ui'),
    path('admin-pandit/pandit/<int:user_id>/reject/', views.reject_pandit_ui, name='reject_pandit_ui'),
    # Profile approval actions (Admin Pandit only)
    path('admin-pandit/profile/<int:profile_id>/approve/', views.approve_profile, name='approve_profile'),
    path('admin-pandit/profile/<int:profile_id>/send-back/', views.send_profile_back_for_edit, name='send_profile_back'),
    # Partial block actions (Admin Pandit only)
    path('admin-pandit/partial-block/apply/', views.apply_partial_block, name='apply_partial_block'),
    path('admin-pandit/partial-block/<int:block_id>/remove/', views.remove_partial_block, name='remove_partial_block'),
]




