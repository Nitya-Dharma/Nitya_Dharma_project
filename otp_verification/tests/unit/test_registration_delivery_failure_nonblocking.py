"""Registration continues when OTP delivery fails. Provider HTTP is never called."""

from __future__ import annotations

import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from bureaus.models import BureauProfile
from core.models import ExpertProfile, ExpertService
from otp_verification.exceptions import (
    ProviderFailureException,
    ProviderTimeoutException,
    ProviderUnavailableException,
)
from otp_verification.registration.responses import ERROR_DELIVERY_FAILED
from profiles.models import PanditProfile
from referrals.models import ReferralLink, ReferralUsage

User = get_user_model()

_DELIVERY_PATCH = (
    "otp_verification.services.orchestration.ProviderOrchestrator.deliver_otp"
)
_FAILURES = (
    ProviderTimeoutException("isolated timeout"),
    ProviderUnavailableException("isolated connection failure"),
    ProviderFailureException("isolated api failure"),
)


@override_settings(
    OTP_ENABLED=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class RegistrationDeliveryFailureNonBlockingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(
            email="admin-delivery-fail@example.test",
            password="testpass123",
            role="admin",
            status="active",
            is_active=True,
        )
        self.referral_link = ReferralLink.objects.create(
            created_by=self.admin,
            token="delivery-fail-tok",
            referral_code="delivery-fail-tok",
            code="REFDELFAIL1",
            max_uses=5,
            used_count=0,
            is_active=True,
            status=ReferralLink.STATUS_ACTIVE,
            expires_at=timezone.now() + timedelta(days=7),
        )
        self.astrology, _ = ExpertService.objects.get_or_create(
            slug="astrology",
            defaults={"name": "Astrology", "display_order": 1},
        )

    def _post(self, url, data, failure):
        with patch(_DELIVERY_PATCH, side_effect=failure) as deliver:
            response = self.client.post(url, data)
        return response, deliver

    def _assert_unverified_once(self, email):
        users = User.objects.filter(email__iexact=email)
        self.assertEqual(users.count(), 1)
        user = users.get()
        self.assertFalse(user.is_phone_verified)
        return user

    def test_pandit_registration_continues_when_delivery_fails(self):
        url = reverse(
            "accounts:pandit_register",
            kwargs={"referral_token": self.referral_link.token},
        )
        for index, failure in enumerate(_FAILURES):
            with self.subTest(failure=type(failure).__name__):
                email = f"pandit-delivery-{index}@example.test"
                before_profiles = PanditProfile.objects.count()
                response, deliver = self._post(
                    url,
                    {
                        "referral_code": self.referral_link.referral_code,
                        "first_name": "Delivery",
                        "last_name": "Pandit",
                        "email": email,
                        "password": "securepass123",
                        "phone_number": f"900000010{index}",
                    },
                    failure,
                )
                self.assertEqual(response.status_code, 200)
                deliver.assert_called_once()
                user = self._assert_unverified_once(email)
                self.assertEqual(user.role, "pandit")
                self.assertEqual(user.status, "pending")
                self.assertFalse(user.is_active)
                self.assertEqual(PanditProfile.objects.filter(user=user).count(), 1)
                self.assertEqual(
                    ReferralUsage.objects.filter(referred_pandit=user).count(),
                    1,
                )
                self.assertEqual(PanditProfile.objects.count(), before_profiles + 1)
                skip = self.client.post(
                    reverse("accounts:pandit_register_skip_phone_otp")
                )
                self.assertEqual(skip.status_code, 302)
                self._assert_unverified_once(email)

    def test_expert_registration_continues_when_delivery_fails(self):
        url = reverse("expert_register") + "?type=astrology"
        for index, failure in enumerate(_FAILURES):
            with self.subTest(failure=type(failure).__name__):
                email = f"expert-delivery-{index}@example.test"
                response, deliver = self._post(
                    url,
                    {
                        "name": "Delivery Fail Expert",
                        "email": email,
                        "password": "StrongPass123!",
                        "confirm_password": "StrongPass123!",
                        "phone": f"900000020{index}",
                        "experience_years": "4",
                        "description": "Isolated delivery failure",
                        "social_links[]": ["https://example.test/expert"],
                        "services": [str(self.astrology.id)],
                    },
                    failure,
                )
                self.assertEqual(response.status_code, 200)
                deliver.assert_called_once()
                user = self._assert_unverified_once(email)
                self.assertEqual(user.role, "user")
                expert = ExpertProfile.objects.get(email=email)
                self.assertFalse(expert.is_active)
                skip = self.client.post(reverse("expert_register_skip_phone_otp"))
                self.assertEqual(skip.status_code, 302)
                self._assert_unverified_once(email)

    def test_bureau_registration_continues_when_delivery_fails(self):
        url = reverse("bureaus:bureau_register")
        for index, failure in enumerate(_FAILURES):
            with self.subTest(failure=type(failure).__name__):
                cache.clear()
                email = f"bureau-delivery-{index}@example.test"
                response, deliver = self._post(
                    url,
                    {
                        "bureau_name": "Delivery Fail Bureau",
                        "email": email,
                        "password": "BureauTestPass123!",
                        "confirm_password": "BureauTestPass123!",
                        "phone_number": f"900000030{index}",
                        "address": "1 Isolated Road",
                        "city": "Hyderabad",
                        "whatsapp_number": "",
                    },
                    failure,
                )
                self.assertEqual(response.status_code, 201)
                deliver.assert_called_once()
                user = self._assert_unverified_once(email)
                self.assertEqual(user.role, "user")
                self.assertEqual(
                    BureauProfile.objects.filter(user=user).count(),
                    1,
                )
                skip = self.client.post(
                    reverse("bureaus:bureau_register_skip_phone_otp")
                )
                self.assertEqual(skip.status_code, 302)
                self._assert_unverified_once(email)

    def test_user_registration_survives_later_delivery_failure(self):
        for index, failure in enumerate(_FAILURES):
            with self.subTest(failure=type(failure).__name__):
                self.client.logout()
                email = f"user-delivery-{index}@example.test"
                phone = f"900000040{index}"
                with patch(_DELIVERY_PATCH) as during_register:
                    created = self.client.post(
                        reverse("accounts:register"),
                        {
                            "email": email,
                            "password": "UserTestPass123!",
                            "password_confirm": "UserTestPass123!",
                            "first_name": "Delivery",
                            "last_name": "User",
                            "phone_number": phone,
                        },
                    )
                during_register.assert_not_called()
                self.assertEqual(created.status_code, 200)
                user = self._assert_unverified_once(email)
                self.assertEqual(user.role, "user")
                self.assertTrue(user.is_active)
                before = User.objects.count()
                with patch(_DELIVERY_PATCH, side_effect=failure):
                    sent = self.client.post(
                        reverse("otp_verification:send_registration_otp"),
                        {
                            "phone_number": phone,
                            "flow_type": "user_registration",
                        },
                    )
                self.assertEqual(sent.status_code, 502)
                body = json.loads(sent.content.decode("utf-8"))
                self.assertEqual(body["error"], ERROR_DELIVERY_FAILED)
                self.assertEqual(User.objects.count(), before)
                self._assert_unverified_once(email)
