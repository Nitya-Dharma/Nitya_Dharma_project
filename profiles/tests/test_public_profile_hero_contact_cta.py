"""Regression: public profile hero Call/WhatsApp CTAs use canonical phone fields."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from profiles.models import PanditProfile


User = get_user_model()

HERO_WA_BTN = 'class="btn btn-success btn-lg whatsapp-btn-hero"'


def _approved_pandit(*, email, **profile_fields):
    user = User.objects.create_user(
        email=email,
        password="PanditTestPass123!",
        first_name="Hero",
        last_name="Pandit",
        role="pandit",
        status="active",
        is_active=True,
        email_verified=True,
    )
    profile, _ = PanditProfile.objects.get_or_create(user=user)
    profile.is_profile_approved = True
    profile.enable_call = True
    profile.allow_call = True
    profile.enable_whatsapp = True
    profile.allow_whatsapp = True
    for key, value in profile_fields.items():
        setattr(profile, key, value)
    profile.save()
    return user, profile


class PublicProfileHeroContactCtaTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _get_public(self, profile):
        return self.client.get(
            reverse("profiles:profile_public_by_id", kwargs={"public_id": profile.public_id})
        )

    def test_hero_call_available_with_canonical_call_mobile_only(self):
        _user, profile = _approved_pandit(
            email="hero-call-only@example.com",
            call_mobile_number="9123456801",
            whatsapp_mobile_number=None,
            primary_mobile_number=None,
            phone_number=None,
        )
        resp = self._get_public(profile)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertIn('href="tel:9123456801"', content)
        self.assertNotIn(HERO_WA_BTN, content)

    def test_hero_whatsapp_available_with_canonical_whatsapp_only(self):
        _user, profile = _approved_pandit(
            email="hero-wa-only@example.com",
            call_mobile_number=None,
            whatsapp_mobile_number="9123456802",
            primary_mobile_number=None,
            phone_number=None,
        )
        resp = self._get_public(profile)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertIn(HERO_WA_BTN, content)
        self.assertIn("wa.me/9123456802", content)
        self.assertNotIn('href="tel:', content)

    def test_hero_legacy_phone_fallback_still_works(self):
        _user, profile = _approved_pandit(
            email="hero-legacy@example.com",
            call_mobile_number=None,
            whatsapp_mobile_number=None,
            primary_mobile_number="9123456803",
            phone_number=None,
        )
        resp = self._get_public(profile)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertIn('href="tel:9123456803"', content)
        self.assertIn(HERO_WA_BTN, content)

    def test_hero_no_phone_hides_contact_ctas(self):
        _user, profile = _approved_pandit(
            email="hero-nophone@example.com",
            call_mobile_number=None,
            whatsapp_mobile_number=None,
            primary_mobile_number=None,
            phone_number=None,
        )
        resp = self._get_public(profile)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertNotIn('href="tel:', content)
        self.assertNotIn(HERO_WA_BTN, content)
