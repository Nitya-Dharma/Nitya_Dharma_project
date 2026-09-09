"""Regression: Super Admin Advertisement create/edit GET must not KeyError on floating.

Floating is a released placement without a dedicated image_floating field.
Does not cover Native Ads, Interstitial, tracking, or Lead/CRM changes.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ads.models import Advertisement
from ads.views import _placement_upload_choices
from ads.forms import AdvertisementForm

User = get_user_model()

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_SLOT_UPLOAD_PLACEMENTS = (
    "top",
    "sidebar",
    "footer",
    "in_content",
    "dashboard_top",
    "dashboard_sidebar",
)


def _script_ad(**kwargs):
    defaults = {
        "name": "Create Edit Ad",
        "placement": "top",
        "slots": ["top"],
        "ad_type": Advertisement.AD_TYPE_SCRIPT,
        "script_code": "<div>ad</div>",
        "is_active": True,
        "redirect_url": "https://advertiser.example/landing",
    }
    defaults.update(kwargs)
    return Advertisement.objects.create(**defaults)


class PlacementUploadChoicesFloatingSkipTests(TestCase):
    def test_floating_is_in_placement_choices_but_not_slot_image_fields(self):
        values = [value for value, _label in Advertisement.PLACEMENT_CHOICES]
        self.assertIn("floating", values)
        self.assertNotIn("floating", Advertisement.SLOT_IMAGE_FIELDS)

    def test_helper_skips_floating_and_keeps_dedicated_upload_slots(self):
        form = AdvertisementForm()
        choices = _placement_upload_choices(form)
        slots = [slot for slot, _label, _field, _size in choices]
        self.assertNotIn("floating", slots)
        self.assertEqual(tuple(slots), _SLOT_UPLOAD_PLACEMENTS)
        for slot, _label, field, _size in choices:
            self.assertEqual(field.name, Advertisement.SLOT_IMAGE_FIELDS[slot])


class AdvertisementCreateEditGetTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_USER_AGENT=_BROWSER_UA)
        self.superuser = User.objects.create_superuser(
            email="ad-form-super@example.com",
            password="test-pass-12345",
        )
        self.user = User.objects.create_user(
            email="ad-form-user@example.com",
            password="test-pass-12345",
            role="user",
        )
        self.pandit = User.objects.create_user(
            email="ad-form-pandit@example.com",
            password="test-pass-12345",
            role="pandit",
        )
        self.admin_role = User.objects.create_user(
            email="ad-form-adminrole@example.com",
            password="test-pass-12345",
            role="admin",
            is_staff=True,
        )

    def test_super_admin_create_get_returns_200(self):
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("ads:advertisement_create"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("floating", html)
        upload_slots = [slot for slot, _label, _field, _size in resp.context["placement_upload_choices"]]
        self.assertNotIn("floating", upload_slots)
        for slot in _SLOT_UPLOAD_PLACEMENTS:
            self.assertIn(slot, upload_slots)
        slot_values = [value for value, _label in resp.context["placement_choices"]]
        self.assertIn("floating", slot_values)
        self.assertNotIn("image_floating", resp.context["slot_image_field_names"])

    def test_super_admin_edit_get_existing_placement_returns_200(self):
        ad = _script_ad(name="Top Ad")
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("ads:advertisement_edit", kwargs={"pk": ad.pk}))
        self.assertEqual(resp.status_code, 200)
        upload_slots = [slot for slot, _label, _field, _size in resp.context["placement_upload_choices"]]
        self.assertNotIn("floating", upload_slots)
        for slot in _SLOT_UPLOAD_PLACEMENTS:
            self.assertIn(slot, upload_slots)

    def test_super_admin_edit_get_floating_advertisement_returns_200(self):
        ad = _script_ad(
            name="Floating Ad",
            placement="floating",
            slots=["floating"],
        )
        self.client.force_login(self.superuser)
        resp = self.client.get(reverse("ads:advertisement_edit", kwargs={"pk": ad.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Floating")

    def test_unauthorized_create_get_is_404(self):
        create_url = reverse("ads:advertisement_create")
        self.assertEqual(self.client.get(create_url).status_code, 404)
        for user in (self.user, self.pandit, self.admin_role):
            client = Client(HTTP_USER_AGENT=_BROWSER_UA)
            client.force_login(user)
            self.assertEqual(client.get(create_url).status_code, 404)

    def test_unauthorized_edit_get_is_404(self):
        ad = _script_ad(name="Perm Ad")
        edit_url = reverse("ads:advertisement_edit", kwargs={"pk": ad.pk})
        self.assertEqual(self.client.get(edit_url).status_code, 404)
        for user in (self.user, self.pandit, self.admin_role):
            client = Client(HTTP_USER_AGENT=_BROWSER_UA)
            client.force_login(user)
            self.assertEqual(client.get(edit_url).status_code, 404)

    def test_super_admin_create_post_still_redirects(self):
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse("ads:advertisement_create"),
            {
                "name": "Posted Script Ad",
                "slots": ["top"],
                "ad_type": Advertisement.AD_TYPE_SCRIPT,
                "script_code": "<div>posted</div>",
                "is_active": "on",
                "is_responsive": "on",
                "redirect_url": "https://advertiser.example/landing",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Advertisement.objects.filter(name="Posted Script Ad").exists())

    def test_super_admin_create_post_floating_slot_still_saves(self):
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse("ads:advertisement_create"),
            {
                "name": "Posted Floating Ad",
                "slots": ["floating"],
                "ad_type": Advertisement.AD_TYPE_SCRIPT,
                "script_code": "<div>float</div>",
                "is_active": "on",
                "is_responsive": "on",
                "redirect_url": "https://advertiser.example/landing",
            },
        )
        self.assertEqual(resp.status_code, 302)
        ad = Advertisement.objects.get(name="Posted Floating Ad")
        self.assertEqual(ad.slots, ["floating"])
        self.assertEqual(ad.placement, "floating")

    def test_super_admin_edit_post_still_redirects(self):
        ad = _script_ad(name="Before Edit")
        self.client.force_login(self.superuser)
        resp = self.client.post(
            reverse("ads:advertisement_edit", kwargs={"pk": ad.pk}),
            {
                "name": "After Edit",
                "slots": ["top", "footer"],
                "ad_type": Advertisement.AD_TYPE_SCRIPT,
                "script_code": "<div>edited</div>",
                "is_active": "on",
                "is_responsive": "on",
                "redirect_url": "https://advertiser.example/landing",
            },
        )
        self.assertEqual(resp.status_code, 302)
        ad.refresh_from_db()
        self.assertEqual(ad.name, "After Edit")
        self.assertEqual(ad.slots, ["top", "footer"])


@override_settings(ENABLE_FLOATING_ADS=True)
class FloatingServingUnchangedTests(TestCase):
    def test_floating_still_serves_and_skips_dashboard(self):
        from django.contrib.auth.models import AnonymousUser
        from django.test import RequestFactory

        from ads.context_processors import active_ads

        ad = _script_ad(
            name="Serve Float",
            placement="floating",
            slots=["floating"],
        )
        factory = RequestFactory()
        public = factory.get("/")
        public.user = AnonymousUser()
        result = active_ads(public)
        self.assertEqual(result["ads_floating"].pk, ad.pk)
        self.assertTrue(result["show_floating_ad"])

        dash = factory.get("/dashboard/super-admin/")
        dash.user = AnonymousUser()
        dash_result = active_ads(dash)
        self.assertFalse(dash_result["show_floating_ad"])
