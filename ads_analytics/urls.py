from django.urls import path
from . import views

app_name = "ads_analytics"

urlpatterns = [
    path("click/<int:ad_id>/", views.track_click, name="track_click"),
    path("impression/<int:ad_id>/", views.track_impression, name="track_impression"),
    path("whatsapp/", views.track_whatsapp_redirect, name="track_whatsapp"),
    path("dashboard/advertiser/<int:ad_id>/", views.advertiser_dashboard_view, name="advertiser_dashboard"),
    path("dashboard/pandit/<int:pandit_id>/", views.pandit_ad_dashboard_view, name="pandit_ad_dashboard"),
    path("dashboard/admin/", views.admin_ad_intelligence_view, name="admin_ad_intelligence"),
]
