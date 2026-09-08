"""Super Admin Ads Lead list URLs.

Mounted at /dashboard/super-admin/advertisements/leads/.
"""

from django.urls import path

from . import views_ad_leads

app_name = "ads_leads"

urlpatterns = [
    path("", views_ad_leads.ad_lead_list, name="ad_lead_list"),
    path(
        "<int:lead_id>/status/",
        views_ad_leads.update_ad_lead_status,
        name="update_ad_lead_status",
    ),
]
