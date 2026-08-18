"""
City-focused SEO landing pages for expert services.

Read-only queryset filters — does not alter existing astrology/numerology/palmistry listing views.
"""
import re
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Case, IntegerField, Prefetch, Q, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST

from core.models import ExpertProfile, ExpertService

from .expert_discovery import experts_offering
from .models import ExpertBookingIntent
from .views_expert_ui import get_expert_by_user

_SERVICE_EXPERT_TYPES = {"ASTROLOGER", "NUMEROLOGIST", "PALMIST"}


def _normalize_phone(phone):
    """Digits only: spaces, +, dashes, etc. removed (duplicate/cooldown + DB consistency)."""
    return re.sub(r"\D", "", phone or "")


def _is_rate_limited(key, limit, window_seconds):
    try:
        if cache.add(key, 1, timeout=window_seconds):
            return False
        try:
            current = cache.incr(key)
        except Exception:
            cache.add(key, 1, timeout=window_seconds)
            return False
        return current > limit
    except Exception:
        return False


def _city_display_label(city_slug):
    return (city_slug or "").replace("-", " ").strip().title()


def _experts_for_city_slug(service_slug, city):
    """Name/description match only (no schema changes); capped for relevance and performance."""
    city_slug = (city or "").replace("-", " ").strip()
    if not city_slug:
        return ExpertProfile.objects.none()
    return (
        experts_offering(service_slug).filter(
            Q(description__icontains=city_slug) | Q(name__icontains=city_slug)
        )
        .prefetch_related(
            Prefetch(
                "services",
                queryset=ExpertService.objects.filter(is_active=True),
                to_attr="active_services",
            )
        )
        .annotate(
            match_priority=Case(
                When(description__icontains=city_slug, then=1),
                When(name__icontains=city_slug, then=2),
                default=3,
                output_field=IntegerField(),
            )
        )
        .order_by("match_priority", "-experience_years", "name")[:50]
    )


def astrology_city_view(request, city):
    experts = _experts_for_city_slug("astrology", city)
    return render(
        request,
        "services/astrology_city.html",
        {
            "experts": experts,
            "city": _city_display_label(city),
            "service_name": "astrology",
        },
    )


def numerology_city_view(request, city):
    experts = _experts_for_city_slug("numerology", city)
    return render(
        request,
        "services/numerology_city.html",
        {
            "experts": experts,
            "city": _city_display_label(city),
            "service_name": "numerology",
        },
    )


def palmistry_city_view(request, city):
    experts = _experts_for_city_slug("palmistry", city)
    return render(
        request,
        "services/palmistry_city.html",
        {
            "experts": experts,
            "city": _city_display_label(city),
            "service_name": "palmistry",
        },
    )


def _expert_booking_redirect(expert_id):
    """PRG target after POST (same URL name as services.urls; no app namespace on include)."""
    return redirect(reverse("expert_profile", args=[expert_id]) + "#booking")


@require_POST
@login_required
def expert_booking_intent_view(request, expert_id):
    client_ip = request.META.get("REMOTE_ADDR") or "unknown"
    rate_limit_key = f"expert_intent:{client_ip}"
    if _is_rate_limited(rate_limit_key, 5, 300):
        messages.error(request, "Unable to process your request.")
        return _expert_booking_redirect(expert_id)

    name = (request.POST.get("name") or "").strip()
    if not name:
        messages.error(request, "Please enter your name.")
        return _expert_booking_redirect(expert_id)

    phone = (request.POST.get("phone") or "").strip()
    phone = _normalize_phone(phone)
    message = strip_tags((request.POST.get("message") or "").strip())

    # strip_tags removes HTML, but we still enforce:
    # - non-empty
    # - reasonable length
    # to prevent abuse/spam payloads
    if not message:
        messages.error(request, "Please enter your requirement.")
        return _expert_booking_redirect(expert_id)

    if len(message) > 2000:
        messages.error(request, "Message is too long.")
        return _expert_booking_redirect(expert_id)

    # Phone stored as digits-only for consistent duplicate/cooldown checks.
    if not phone or not phone.isdigit() or not (8 <= len(phone) <= 15):
        messages.error(request, "Please enter a valid phone number.")
        return _expert_booking_redirect(expert_id)

    errors = []
    if len(name) > 150:
        errors.append("Name is too long.")

    if errors:
        for err in errors:
            messages.error(request, err)
        return _expert_booking_redirect(expert_id)

    try:
        with transaction.atomic():
            # Lock parent expert first so concurrent posts serialize when no intent row
            # exists yet (select_for_update on an empty intent queryset would not lock).
            expert = (
                ExpertProfile.objects.select_for_update(of=("self",))
                .get(id=expert_id, is_active=True)
            )
            if expert.expert_type not in _SERVICE_EXPERT_TYPES:
                messages.error(request, "Unable to process your request.")
                return _expert_booking_redirect(expert.id)

            existing = (
                ExpertBookingIntent.objects.select_for_update()
                .filter(
                    expert=expert,
                    user=request.user,
                    is_viewed=False,
                )
                .first()
            )
            if existing:
                messages.warning(request, "You already have a pending request.")
                return _expert_booking_redirect(expert_id)

            cooldown_window = timezone.now() - timedelta(minutes=10)
            if ExpertBookingIntent.objects.filter(
                expert=expert,
                phone=phone,
                created_at__gte=cooldown_window,
            ).exists():
                messages.error(
                    request,
                    "Please wait before submitting another request.",
                )
                return _expert_booking_redirect(expert_id)

            ExpertBookingIntent.objects.create(
                expert=expert,
                user=request.user,
                name=name,
                phone=phone,
                message=message,
            )
    except ExpertProfile.DoesNotExist:
        messages.error(request, "Unable to process your request.")
        return redirect(reverse("core:home"))
    except IntegrityError:
        messages.warning(request, "You already have a pending request.")
        return _expert_booking_redirect(expert_id)
    except Exception:
        messages.error(request, "Unable to process your request.")
        return _expert_booking_redirect(expert_id)

    # PRG: always redirect after successful POST so refresh cannot resubmit.
    messages.success(request, "Your booking request has been sent.")
    return _expert_booking_redirect(expert_id)


@require_POST
@login_required
def mark_expert_intent_viewed(request, intent_id):
    """POST-only: CSRF + method guard (no GET side effects)."""
    # Ownership resolved via get_expert_by_user to avoid email-based ambiguity.
    expert = get_expert_by_user(request.user)
    if not expert:
        return redirect("/dashboard/user/")

    intent = get_object_or_404(
        ExpertBookingIntent,
        id=intent_id,
        expert=expert,
    )
    if not intent.is_viewed:
        intent.is_viewed = True
        intent.save(update_fields=["is_viewed"])

    return redirect("/dashboard/expert/?tab=requests")
