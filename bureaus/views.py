import uuid
import json
import logging
import re
from datetime import timedelta

"""
IMPORTANT:
All BureauProfile access MUST go through:
- get_bureau_for_user
- get_bureau_by_user_or_404

Do NOT use direct ORM queries for user-owned bureau access.
This ensures isolation and prevents cross-domain leakage.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST

from .models import BureauBookingIntent, BureauProfile, BureauReview
from .utils import (
    get_bureau_by_user_or_404,
    get_bureau_for_user,
    get_owned_email_verified_bureau,
    get_visible_bureaus,
)

logger = logging.getLogger(__name__)

# Caste filter dropdown source-of-truth.
# Order: (category_label, [(value, display_label), ...]). The value is the
# lowercased canonical key — bureaus store capitalized strings (e.g. "Vysya")
# in caste_data, but `_bureau_has_caste` already lowercases both sides before
# comparing, so these keys round-trip safely. ALLOWED_CASTES is derived from
# this list to guarantee the validator and the UI never drift.
CASTE_GROUPS = (
    ("OC (Open Category / Forward Castes)", (
        ("brahmin", "Brahmin"),
        ("reddy", "Reddy"),
        ("kamma", "Kamma"),
        ("vysya", "Vysya / Bania (Agarwal, Gupta, Maheshwari)"),
        ("rajput", "Rajput"),
        ("kshatriya", "Kshatriya (Raju)"),
        ("velama", "Velama"),
        ("kapu", "Kapu (Turpu Kapu, Balija)"),
        ("nair", "Nair"),
        ("kayastha", "Kayastha"),
        ("khatri", "Khatri"),
    )),
    ("OBC (Other Backward Classes)", (
        ("yadav", "Yadav / Golla"),
        ("goud", "Goud / Ediga"),
        ("munnuru kapu", "Munnuru Kapu"),
        ("padmashali", "Padmashali"),
        ("mudiraj", "Mudiraj"),
        ("kuruma", "Kuruma / Kuruba"),
        ("vishwakarma", "Vishwakarma (Goldsmith, Carpenter, Blacksmith)"),
        ("nai", "Nai (Barber)"),
        ("kumhar", "Kumhar (Potter)"),
        ("dhobi", "Dhobi (Chakali)"),
        ("jat", "Jat"),
        ("lodh", "Lodh"),
        ("gujjar", "Gujjar"),
        ("vanjari", "Vanjari"),
    )),
    ("SC (Scheduled Castes)", (
        ("mala", "Mala"),
        ("madiga", "Madiga"),
        ("jatav", "Jatav / Chamar"),
        ("mahar", "Mahar"),
        ("valmiki", "Valmiki"),
        ("adi dravida", "Adi Dravida"),
        ("pasi", "Pasi"),
        ("dhanuk", "Dhanuk"),
        ("meghwal", "Meghwal"),
        ("khatik", "Khatik"),
    )),
    ("ST (Scheduled Tribes)", (
        ("lambada", "Lambada / Banjara"),
        ("gond", "Gond"),
        ("koya", "Koya"),
        ("chenchu", "Chenchu"),
        ("santhal", "Santhal"),
        ("bhil", "Bhil"),
        ("meena", "Meena"),
        ("yerukala", "Yerukala"),
        ("munda", "Munda"),
        ("bodo", "Bodo"),
    )),
)

ALLOWED_CASTES = {value for _label, items in CASTE_GROUPS for value, _display in items}
ALLOWED_CASTE_CATEGORIES = {"OC", "OBC", "SC", "ST"}


def _normalize_email(value):
    return (value or "").strip().lower()


def _email_exists_ci(user_model, normalized_email):
    return user_model.objects.filter(email__iexact=normalized_email).exists()


def get_visible_bureaus_queryset():
    return get_visible_bureaus()


def _build_random_bureau_username():
    return f"bureau_{uuid.uuid4().hex[:12]}"


def _normalize_caste_data(caste_data):
    if not isinstance(caste_data, dict):
        return {}

    normalized = {}
    for category, values in caste_data.items():
        if category not in ALLOWED_CASTE_CATEGORIES:
            continue
        if isinstance(values, str):
            cleaned_values = [values.strip()] if values.strip() else []
        elif isinstance(values, list):
            cleaned_values = [str(v).strip() for v in values if str(v).strip()]
        else:
            continue
        # Deduplicate while preserving input order for deterministic display.
        cleaned_values = list(dict.fromkeys(cleaned_values))
        normalized[category] = cleaned_values
    return normalized


def _bureau_has_caste(profile, caste_value):
    caste_data = _normalize_caste_data(profile.caste_data or {})
    for values in caste_data.values():
        normalized_values = {str(v).strip().lower() for v in values}
        if caste_value in normalized_values:
            return True
    return False


def _is_valid_caste_data_structure(caste_data):
    if not isinstance(caste_data, dict):
        return False
    if set(caste_data.keys()) - ALLOWED_CASTE_CATEGORIES:
        return False
    for values in caste_data.values():
        if not isinstance(values, (str, list)):
            return False
    return True


def _build_caste_sections(caste_data):
    sections = []
    ordered_categories = ("OC", "OBC", "SC", "ST")
    safe_data = _normalize_caste_data(caste_data)

    for category in ordered_categories:
        values = safe_data.get(category, [])
        cleaned = [str(value).strip() for value in values if str(value).strip()]
        if cleaned:
            sections.append({"category": category, "values": cleaned})
    return sections


def _sanitize_description(value):
    # Enforce plain-text storage to avoid HTML/script payload persistence.
    return strip_tags(value or "").strip()


def _normalize_phone(value):
    raw = (value or "").strip()
    if not raw:
        return ""

    has_plus_prefix = raw.startswith("+")
    digits_only = re.sub(r"\D", "", raw)
    if not digits_only:
        return ""
    return f"+{digits_only}" if has_plus_prefix else digits_only


def _is_valid_phone(value):
    # Accept E.164-like format or plain digits for local storage consistency.
    return bool(re.fullmatch(r"\+?\d{8,15}", value or ""))


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
        # Fail open: never break request flow if cache is unavailable.
        return False


@require_http_methods(["GET"])
def bureau_list_view(request):
    city = (request.GET.get("city") or "").strip()
    caste = (request.GET.get("caste") or "").strip().lower()

    list_only_fields = (
        "id",
        "public_id",
        "bureau_name",
        "city",
        "profile_image",
        "description",
    )

    bureaus_qs = get_visible_bureaus_queryset().only(*list_only_fields).order_by("-created_at", "-id")

    if city:
        bureaus_qs = bureaus_qs.filter(city=city)

    bureaus_data = bureaus_qs
    is_capped = False
    safe_caste_filter = ""
    if caste and caste not in ALLOWED_CASTES:
        bureaus_data = []
    elif caste:
        # caste_data is required only when caste filtering is requested.
        bureaus_qs = bureaus_qs.only(*list_only_fields, "caste_data")
        caste_filter_soft_cap = 500
        ordered_bureaus = list(bureaus_qs.iterator(chunk_size=100))
        filtered_bureaus = []
        for bureau in ordered_bureaus:
            if _is_valid_caste_data_structure(bureau.caste_data) and _bureau_has_caste(bureau, caste):
                filtered_bureaus.append(bureau)
        if len(filtered_bureaus) > caste_filter_soft_cap:
            is_capped = True
            logger.warning(
                "Caste filtering soft cap reached for bureau_list_view; limiting matched results to %s rows",
                caste_filter_soft_cap,
            )
            filtered_bureaus = filtered_bureaus[:caste_filter_soft_cap]
        bureaus_data = filtered_bureaus
        safe_caste_filter = caste

    paginator = Paginator(bureaus_data, 12)
    page_number = request.GET.get("page")
    bureaus_page = paginator.get_page(page_number)

    return render(
        request,
        "bureaus/list.html",
        {
            "bureaus": bureaus_page,
            "city_filter": city,
            "caste_filter": safe_caste_filter,
            "caste_groups": CASTE_GROUPS,
            "is_capped": is_capped,
        },
    )


@require_http_methods(["GET"])
def bureau_detail_view(request, public_id):
    try:
        bureau_profile = get_visible_bureaus_queryset().only(
            "public_id",
            "bureau_name",
            "description",
            "city",
            "profile_image",
            "cover_image",
            "phone_number",
            "whatsapp_number",
            "caste_data",
        ).get(public_id=public_id)
    except BureauProfile.DoesNotExist:
        return redirect("/bureaus/")

    has_active_intent = False
    if request.user.is_authenticated:
        has_active_intent = BureauBookingIntent.objects.filter(
            bureau=bureau_profile,
            user=request.user,
            is_viewed=False,
        ).exists()

    caste_sections = _build_caste_sections(bureau_profile.caste_data)
    reviews_qs = bureau_profile.reviews.only("rating", "review_text", "created_at").order_by("-created_at")[:10]
    review_summary = bureau_profile.reviews.aggregate(avg_rating=Avg("rating"), review_count=Count("id"))
    bureau_data = {
        "public_id": bureau_profile.public_id,
        "name": bureau_profile.bureau_name,
        "description": bureau_profile.description,
        "city": bureau_profile.city,
        "profile_image": bureau_profile.profile_image.url if bureau_profile.profile_image else None,
        "cover_image": bureau_profile.cover_image.url if bureau_profile.cover_image else None,
        "phone": bureau_profile.phone_number,
        "whatsapp": bureau_profile.whatsapp_number,
        "caste_sections": caste_sections,
        "reviews": [
            {
                "rating": item.rating,
                "review_text": item.review_text,
                "created_at": item.created_at,
            }
            for item in reviews_qs
        ],
        "avg_rating": round(float(review_summary.get("avg_rating") or 0.0), 1),
        "review_count": int(review_summary.get("review_count") or 0),
    }
    return render(
        request,
        "bureaus/detail.html",
        {
            "bureau": bureau_data,
            "bureau_profile": bureau_profile,
            "has_active_intent": has_active_intent,
        },
    )


@require_POST
@login_required
def bureau_booking_intent_view(request, public_id):
    client_ip = request.META.get("REMOTE_ADDR") or "unknown"
    rate_limit_key = f"intent:{client_ip}"
    if _is_rate_limited(rate_limit_key, 5, 300):
        messages.error(request, "Unable to process your request.")
        return redirect(f"/bureaus/{public_id}/")

    name = (request.POST.get("name") or "").strip()
    if not name:
        messages.error(request, "Please enter your name.")
        return redirect(
            reverse("bureaus:bureau_detail", kwargs={"public_id": public_id})
            + "#booking"
        )

    phone = request.POST.get("phone") or ""
    phone = _normalize_phone(phone)
    message = (request.POST.get("message") or "").strip()

    errors = []
    if not phone:
        errors.append("Phone is required.")
    elif not _is_valid_phone(phone):
        errors.append("Phone format is invalid.")
    if len(name) > 150:
        errors.append("Name is too long.")
    if len(phone) > 20:
        errors.append("Phone is too long.")
    if not message:
        errors.append("Please enter your requirement.")
    elif len(message) > 2000:
        errors.append("Message is too long.")

    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect(
            reverse("bureaus:bureau_detail", kwargs={"public_id": public_id})
            + "#booking"
        )

    bureau_owner = None
    try:
        with transaction.atomic():
            try:
                bureau_profile = (
                    get_visible_bureaus_queryset()
                    .select_for_update(of=("self",))
                    .get(public_id=public_id)
                )
            except BureauProfile.DoesNotExist:
                messages.error(request, "Unable to process your request.")
                return redirect("/bureaus/")

            existing_intent = (
                BureauBookingIntent.objects.select_for_update()
                .filter(
                    bureau=bureau_profile,
                    user=request.user,
                    is_viewed=False,
                )
                .first()
            )

            if existing_intent:
                messages.warning(
                    request,
                    "You already have a pending request.",
                )
                return redirect(
                    reverse(
                        "bureaus:bureau_detail",
                        kwargs={"public_id": public_id},
                    )
                    + "#booking"
                )

            cooldown_window = timezone.now() - timedelta(minutes=10)
            is_duplicate_recent = BureauBookingIntent.objects.filter(
                bureau=bureau_profile,
                phone=phone,
                created_at__gte=cooldown_window,
            ).exists()
            if is_duplicate_recent:
                messages.error(request, "Please wait before submitting another request.")
                return redirect(f"/bureaus/{public_id}/")

            BureauBookingIntent.objects.create(
                bureau=bureau_profile,
                user=request.user,
                name=name,
                phone=phone,
                message=message,
            )
            bureau_owner = bureau_profile.user
    except IntegrityError:
        messages.warning(
            request,
            "You already have a pending request.",
        )
        return redirect(
            reverse("bureaus:bureau_detail", kwargs={"public_id": public_id})
            + "#booking"
        )
    except Exception:
        messages.error(request, "Unable to process your request.")
        return redirect(f"/bureaus/{public_id}/")

    try:
        from ads_analytics.services.attribution_bridge import (
            record_booking_conversion_from_session,
        )
        record_booking_conversion_from_session(request, user_id=request.user.pk)
    except Exception:
        pass

    # Shared Notification for Bureau owner (reuse Pandit-style create_notification).
    # Must not fail the successful booking-intent submission.
    if bureau_owner is not None:
        try:
            from notifications.constants import NOTIFICATION_TYPE_BOOKING_INTENT
            from notifications.services import NotificationService

            NotificationService.create_notification(
                recipient=bureau_owner,
                notification_type=NOTIFICATION_TYPE_BOOKING_INTENT,
                source_module="bureaus",
                payload={
                    "title": "New booking request",
                    "message": (
                        "You received a new booking request for your Marriage Bureau."
                    ),
                    "url": "/dashboard/bureau/?tab=requests",
                },
            )
        except Exception:
            pass

    messages.success(request, "Your booking request has been sent.")
    return redirect(
        reverse("bureaus:bureau_detail", kwargs={"public_id": public_id}) + "#booking"
    )


@require_http_methods(["POST"])
def bureau_review_submit_view(request, public_id):
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to submit a review.")
        return redirect(reverse("accounts:login") + f"?next=/bureaus/{public_id}/")

    rate_limit_key = f"review:{request.user.id}"
    if _is_rate_limited(rate_limit_key, 3, 300):
        messages.error(request, "Unable to process your request.")
        return redirect(f"/bureaus/{public_id}/")

    try:
        bureau_profile = get_visible_bureaus_queryset().only("id", "public_id").get(public_id=public_id)
    except BureauProfile.DoesNotExist:
        messages.error(request, "Unable to process your request.")
        return redirect("/bureaus/")

    rating_raw = (request.POST.get("rating") or "").strip()
    review_text = strip_tags((request.POST.get("review_text") or "").strip())

    errors = []
    try:
        rating = int(rating_raw)
    except (TypeError, ValueError):
        rating = None
        errors.append("Invalid rating value.")

    if rating is not None and not (1 <= rating <= 5):
        errors.append("Rating must be between 1 and 5.")
    if len(review_text) > 2000:
        errors.append("Review is too long.")

    if errors:
        for error in errors:
            messages.error(request, error)
        return redirect(f"/bureaus/{public_id}/")

    with transaction.atomic():
        existing_review = (
            BureauReview.objects.select_for_update()
            .filter(bureau=bureau_profile, user=request.user)
            .first()
        )
        if existing_review:
            existing_review.rating = rating
            existing_review.review_text = review_text
            existing_review.save()
        else:
            BureauReview.objects.create(
                bureau=bureau_profile,
                user=request.user,
                rating=rating,
                review_text=review_text,
            )
    messages.success(request, "Your review has been submitted.")
    return redirect(f"/bureaus/{public_id}/")


@require_POST
@login_required
def mark_intent_viewed(request, intent_id):
    intent = get_object_or_404(
        BureauBookingIntent,
        id=intent_id,
        bureau__user=request.user
    )
    if intent.bureau.user_id != request.user.id:
        return redirect("/dashboard/bureau/?tab=requests")

    if not intent.is_viewed:
        intent.is_viewed = True
        intent.save(update_fields=["is_viewed"])

    return redirect("/dashboard/bureau/?tab=requests&updated=1")


@login_required
@require_POST
def approve_bureau(request, public_id):
    # Super Admin only (same gate pattern as Expert Super Admin actions).
    if not request.user.is_superuser:
        raise Http404("Page not found")

    bureau = get_object_or_404(BureauProfile, public_id=public_id)
    if not bureau.is_approved:
        bureau.is_approved = True
        bureau.save(update_fields=["is_approved"])
    return redirect("/dashboard/super-admin/?tab=bureaus")


@login_required
@require_POST
def activate_bureau(request, public_id):
    # Super Admin only (same gate pattern as approve_bureau).
    if not request.user.is_superuser:
        raise Http404("Page not found")

    bureau = get_object_or_404(BureauProfile, public_id=public_id)
    # Activation requires prior approval; never imply-approve.
    if not bureau.is_approved:
        raise Http404("Page not found")
    if not bureau.is_active:
        bureau.is_active = True
        bureau.save(update_fields=["is_active"])
    return redirect("/dashboard/super-admin/?tab=bureaus")


@login_required
@require_http_methods(["GET"])
def review_bureau(request, public_id):
    """Super Admin read-only review of any Bureau by public_id (not public visibility)."""
    if not request.user.is_superuser:
        raise Http404("Page not found")

    bureau = get_object_or_404(BureauProfile, public_id=public_id)
    return render(
        request,
        "module5_dashboards/bureau_review.html",
        {
            "bureau": bureau,
            # Required by dashboard_base.html to render {% block dashboard_content %}.
            "dashboard_has_data": True,
        },
    )


def _deny_bureau_access(request):
    if not getattr(request.user, "is_authenticated", False):
        login_url = reverse("accounts:login")
        return redirect(f"{login_url}?next=/dashboard/bureau/")
    return redirect("core:home")


def is_valid_bureau_user(user):
    if not getattr(user, "is_authenticated", False):
        return False
    return get_bureau_for_user(user) is not None


def _get_bureau_dashboard_data(profile):
    data = get_visible_bureaus_queryset().filter(id=profile.id).aggregate(
        intents_count=Count("booking_intents", distinct=True),
        review_count=Count("reviews", distinct=True),
        avg_rating=Avg("reviews__rating"),
    )
    intents_count = data["intents_count"] or 0
    review_count = data["review_count"] or 0
    avg_rating = round(float(data["avg_rating"] or 0), 2)
    unread_intents = profile.booking_intents.filter(is_viewed=False).count()
    has_intents = profile.booking_intents.exists()
    recent_intents = list(
        profile.booking_intents
        .only("id", "name", "phone", "is_viewed", "created_at")
        .order_by("-created_at", "-id")[:10]
    )

    return {
        "intents_count": intents_count,
        "review_count": review_count,
        "avg_rating": avg_rating,
        "unread_intents": unread_intents,
        "recent_intents": recent_intents,
        "has_intents": has_intents,
    }


def is_bureau_profile_complete(profile):
    if not profile:
        return False
    if not (profile.description or "").strip():
        return False
    if not (profile.phone_number or "").strip():
        return False
    if not (profile.address or "").strip():
        return False
    if not (profile.city or "").strip():
        return False
    if not profile.caste_data:
        return False
    return True


@require_http_methods(["GET"])
def bureau_dashboard_view(request):
    if not is_valid_bureau_user(request.user):
        return _deny_bureau_access(request)

    try:
        bureau_profile = get_bureau_by_user_or_404(request.user)
    except PermissionDenied:
        return _deny_bureau_access(request)

    bureau_profile = (
        BureauProfile.objects.filter(pk=bureau_profile.pk)
        .select_related("user")
        .prefetch_related("booking_intents__user")
        .get()
    )

    dashboard_data = _get_bureau_dashboard_data(bureau_profile)
    is_profile_edit_view = bool(
        request.resolver_match
        and request.resolver_match.view_name == "bureaus:bureau_profile_edit"
    )
    if not is_bureau_profile_complete(bureau_profile) and not is_profile_edit_view:
        return redirect("/bureaus/profile/edit/")

    return render(
        request,
        "bureaus/dashboard.html",
        {
            "bureau_profile": bureau_profile,
            **dashboard_data,
        },
    )


@require_http_methods(["GET", "POST"])
def bureau_profile_edit_view(request):
    # Owner edit: ownership + email verified only (not approval/activation).
    # Do not use get_bureau_for_user here — that helper means fully eligible.
    if not getattr(request.user, "is_authenticated", False):
        return _deny_bureau_access(request)

    bureau_profile = get_owned_email_verified_bureau(request.user)
    if bureau_profile is None:
        return _deny_bureau_access(request)

    def _bureau_profile_edit_context(bureau, form_data, *, user=None):
        from otp_verification import constants as otp_constants
        from otp_verification.registration.completions import _sync_expert_user_phone
        from otp_verification.registration.factory import is_registration_otp_required

        owner = user
        profile_phone = (bureau.phone_number or "").strip()
        if owner and profile_phone and hasattr(owner, "phone_number"):
            if owner.phone_number != profile_phone:
                _sync_expert_user_phone(owner, profile_phone)

        ctx = {
            "bureau_profile": bureau,
            "form_data": form_data,
            "phone_is_verified": bool(getattr(owner, "is_phone_verified", False))
            if owner
            else False,
            "bureau_otp_required": is_registration_otp_required(
                otp_constants.FLOW_BUREAU_REGISTRATION
            ),
        }
        return ctx

    if request.method == "GET":
        return render(
            request,
            "bureaus/profile_edit.html",
            _bureau_profile_edit_context(
                bureau_profile,
                {
                    "description": bureau_profile.description or "",
                    "phone_number": bureau_profile.phone_number or "",
                    "whatsapp_number": bureau_profile.whatsapp_number or "",
                    "address": bureau_profile.address or "",
                    "city": bureau_profile.city or "",
                    "caste_data": json.dumps(bureau_profile.caste_data or {}, indent=2),
                },
                user=request.user,
            ),
        )

    old_phone_number = (bureau_profile.phone_number or "").strip()

    description = _sanitize_description(request.POST.get("description"))
    phone_number = _normalize_phone(request.POST.get("phone_number"))
    whatsapp_number = _normalize_phone(request.POST.get("whatsapp_number"))
    address = (request.POST.get("address") or "").strip()
    city = (request.POST.get("city") or "").strip()
    caste_data_raw = (request.POST.get("caste_data") or "").strip()

    errors = []
    if not phone_number:
        errors.append("Phone number is required.")
    elif not _is_valid_phone(phone_number):
        errors.append("Phone number format is invalid.")
    if whatsapp_number and not _is_valid_phone(whatsapp_number):
        errors.append("WhatsApp number format is invalid.")
    if not address:
        errors.append("Address is required.")
    if not city:
        errors.append("City is required.")

    parsed_caste_data = {}
    normalized_caste_data = {}
    if not caste_data_raw:
        errors.append("Caste data is required.")
    else:
        try:
            parsed_caste_data = json.loads(caste_data_raw)
            if not isinstance(parsed_caste_data, dict):
                errors.append("Caste data must be a JSON object.")
            elif set(parsed_caste_data.keys()) - ALLOWED_CASTE_CATEGORIES:
                errors.append("Caste data contains invalid categories.")
            elif not parsed_caste_data:
                errors.append("Caste data cannot be empty.")
            else:
                normalized_caste_data = _normalize_caste_data(parsed_caste_data)
                if not normalized_caste_data:
                    errors.append("Caste data cannot be empty.")
        except json.JSONDecodeError:
            errors.append("Caste data must be valid JSON.")

    form_data = {
        "description": description,
        "phone_number": phone_number,
        "whatsapp_number": whatsapp_number,
        "address": address,
        "city": city,
        "caste_data": caste_data_raw,
    }

    if errors:
        for error in errors:
            messages.error(request, error)
        messages.error(request, "Please complete all required fields")
        return render(
            request,
            "bureaus/profile_edit.html",
            _bureau_profile_edit_context(bureau_profile, form_data, user=request.user),
            status=400,
        )

    validated_data = {
        "description": description,
        "phone_number": phone_number,
        "whatsapp_number": whatsapp_number,
        "address": address,
        "city": city,
        "caste_data": normalized_caste_data,
    }

    profile_image = request.FILES.get("profile_image")
    if profile_image:
        validated_data["profile_image"] = profile_image
    elif (request.POST.get("clear_profile_image") or "").strip().lower() in {"1", "true", "on", "yes"}:
        validated_data["profile_image"] = None

    cover_image = request.FILES.get("cover_image")
    if cover_image:
        validated_data["cover_image"] = cover_image
    elif (request.POST.get("clear_cover_image") or "").strip().lower() in {"1", "true", "on", "yes"}:
        validated_data["cover_image"] = None

    # Keep old file references for safe post-save cleanup.
    old_profile_image = bureau_profile.profile_image if bureau_profile.profile_image else None
    old_cover_image = bureau_profile.cover_image if bureau_profile.cover_image else None

    try:
        # Allowed update fields only; status flags are never assigned here.
        for key, value in validated_data.items():
            setattr(bureau_profile, key, value)
        bureau_profile.save()
    except Exception:
        messages.error(request, "Profile update failed. Please try again.")
        return render(
            request,
            "bureaus/profile_edit.html",
            _bureau_profile_edit_context(bureau_profile, form_data, user=request.user),
            status=500,
        )

    from otp_verification.registration.completions import _sync_expert_user_phone

    _sync_expert_user_phone(request.user, phone_number)
    if phone_number != old_phone_number and getattr(request.user, "is_phone_verified", False):
        request.user.is_phone_verified = False
        request.user.save(update_fields=["is_phone_verified", "updated_at"])

    # Delete old files only after successful save.
    if old_profile_image:
        if bureau_profile.profile_image:
            if old_profile_image != bureau_profile.profile_image:
                try:
                    old_profile_image.delete(save=False)
                except Exception:
                    pass
        else:
            try:
                old_profile_image.delete(save=False)
            except Exception:
                pass

    if old_cover_image:
        if bureau_profile.cover_image:
            if old_cover_image != bureau_profile.cover_image:
                try:
                    old_cover_image.delete(save=False)
                except Exception:
                    pass
        else:
            try:
                old_cover_image.delete(save=False)
            except Exception:
                pass

    if not is_bureau_profile_complete(bureau_profile):
        messages.error(request, "Please complete all required fields")
        return render(
            request,
            "bureaus/profile_edit.html",
            _bureau_profile_edit_context(bureau_profile, form_data, user=request.user),
            status=400,
        )

    messages.success(request, "Profile updated successfully.")
    if get_bureau_for_user(request.user) is not None:
        return redirect("/dashboard/bureau/")
    return redirect("bureaus:bureau_owner_status")


@login_required
@require_POST
@csrf_protect
def resend_bureau_verification_view(request):
    """Authenticated Bureau owner self-service email verification resend."""
    from bureaus.services_verification import (
        BureauResendCooldownNotElapsed,
        BureauResendNotAllowed,
        BureauVerificationAlreadyCompleted,
        resend_bureau_verification_email,
    )

    try:
        resend_bureau_verification_email(request.user)
    except BureauVerificationAlreadyCompleted:
        messages.info(
            request,
            "Your email is already verified. No action needed.",
        )
    except BureauResendCooldownNotElapsed as exc:
        messages.warning(request, str(exc))
    except BureauResendNotAllowed:
        messages.error(
            request,
            "Email verification resend is only available for Bureau owner accounts.",
        )
        return redirect("core:home")
    except ValidationError as exc:
        messages.error(request, str(exc))
    except Exception:
        logger.exception(
            "Unexpected error resending Bureau verification for %s",
            getattr(request.user, "email", "unknown"),
        )
        messages.error(
            request,
            "Failed to send verification email. Please try again later.",
        )
    else:
        messages.success(
            request,
            "Verification email has been sent. Please check your inbox and spam folder.",
        )

    return redirect("bureaus:bureau_register")


@login_required
@require_http_methods(["GET"])
def bureau_owner_status_view(request):
    """Read-only Bureau owner onboarding status (email, approval, activation, profile)."""
    try:
        bureau_profile = BureauProfile.objects.get(user=request.user)
    except BureauProfile.DoesNotExist:
        return redirect("core:home")

    eligible_profile = get_bureau_for_user(request.user)
    if eligible_profile and is_bureau_profile_complete(eligible_profile):
        return redirect("/dashboard/bureau/")

    return render(
        request,
        "bureaus/status.html",
        {
            "bureau_profile": bureau_profile,
            "email_verified": bureau_profile.is_email_verified,
            "is_approved": bureau_profile.is_approved,
            "is_active": bureau_profile.is_active,
            "profile_complete": is_bureau_profile_complete(bureau_profile),
        },
    )


@require_http_methods(["POST"])
def bureau_register_skip_phone_otp(request):
    """Complete Bureau registration without OTP verification (bureau flow only)."""

    from otp_verification import constants as otp_constants
    from otp_verification.registration.completions import (
        AlreadyCompletedError,
        CompletionError,
        complete_pending_registration,
    )
    from otp_verification.registration.session import (
        clear_pending_registration,
        get_pending_registration,
    )

    pending = get_pending_registration(request)
    if (
        not pending
        or pending.get("flow_type") != otp_constants.FLOW_BUREAU_REGISTRATION
    ):
        messages.error(
            request,
            "No pending bureau registration found. Please register again.",
        )
        return redirect("bureaus:bureau_register")

    try:
        complete_pending_registration(pending=pending)
    except AlreadyCompletedError:
        pass
    except CompletionError as exc:
        messages.error(request, str(exc))
        return redirect("bureaus:bureau_register")

    clear_pending_registration(request)
    messages.success(request, "Registration successful. Awaiting admin approval.")
    return redirect("bureaus:bureau_register")


@require_http_methods(["GET", "POST"])
def bureau_register_view(request):
    from otp_verification import constants as otp_constants
    from otp_verification.registration.factory import is_registration_otp_required

    bureau_otp_required = is_registration_otp_required(
        otp_constants.FLOW_BUREAU_REGISTRATION
    )

    if request.method == "GET":
        return render(
            request,
            "bureaus/register.html",
            {"bureau_otp_required": bureau_otp_required},
        )

    bureau_name = (request.POST.get("bureau_name") or "").strip()
    email = _normalize_email(request.POST.get("email"))
    password = request.POST.get("password") or ""
    confirm_password = request.POST.get("confirm_password") or ""
    phone_number = _normalize_phone(request.POST.get("phone_number"))
    address = (request.POST.get("address") or "").strip()
    city = (request.POST.get("city") or "").strip()
    whatsapp_number = _normalize_phone(request.POST.get("whatsapp_number"))
    form_data = {
        "bureau_name": bureau_name,
        "email": email,
        "phone_number": phone_number,
        "address": address,
        "city": city,
        "whatsapp_number": whatsapp_number,
    }

    errors = []
    max_bureau_name_len = 255
    max_city_len = 120
    max_address_len = 2000

    if not bureau_name:
        errors.append("Bureau name is required.")
    if not email:
        errors.append("Email is required.")
    if not password:
        errors.append("Password is required.")
    if not confirm_password:
        errors.append("Confirm password is required.")
    if not phone_number:
        errors.append("Phone number is required.")
    elif not _is_valid_phone(phone_number):
        errors.append("Phone number format is invalid.")
    if whatsapp_number and not _is_valid_phone(whatsapp_number):
        errors.append("WhatsApp number format is invalid.")
    if not address:
        errors.append("Address is required.")
    if not city:
        errors.append("City is required.")
    if password and confirm_password and password != confirm_password:
        errors.append("Passwords do not match.")
    if len(bureau_name) > max_bureau_name_len:
        errors.append("Bureau name is too long.")
    if len(city) > max_city_len:
        errors.append("City is too long.")
    if len(address) > max_address_len:
        errors.append("Address is too long.")

    User = get_user_model()
    if email and _email_exists_ci(User, email):
        errors.append("An account with this email already exists.")

    if password:
        try:
            validate_password(password)
        except ValidationError as exc:
            errors.extend(exc.messages)

    if errors:
        for error in errors:
            messages.error(request, error)
        return render(
            request,
            "bureaus/register.html",
            {"form_data": form_data},
            status=400,
        )

    client_ip = request.META.get("REMOTE_ADDR") or "unknown"
    rate_limit_key = f"register:{client_ip}"
    if _is_rate_limited(rate_limit_key, 3, 600):
        messages.error(request, "Unable to process your request.")
        return render(request, "bureaus/register.html", status=429)

    from otp_verification.registration.gate import begin_otp_or_continue

    skip_phone_verification = request.POST.get("skip_phone_verification") == "1"
    if bureau_otp_required and not skip_phone_verification:
        otp_response = begin_otp_or_continue(
            request,
            flow_type=otp_constants.FLOW_BUREAU_REGISTRATION,
            destination=phone_number,
            payload={
                "bureau_name": bureau_name,
                "email": email,
                "password": password,
                "phone_number": phone_number,
                "address": address,
                "city": city,
                "whatsapp_number": whatsapp_number,
            },
            resume_path="/bureaus/register/",
        )
        if otp_response is not None:
            if otp_response.status_code == 400:
                return render(
                    request,
                    "bureaus/register.html",
                    {"form_data": form_data},
                    status=400,
                )
            return otp_response

    try:
        with transaction.atomic():
            # Email uniqueness is intentionally enforced at application level.
            # Any future module creating users by email must follow this same rule.
            if _email_exists_ci(User, email):
                raise ValidationError("An account with this email already exists.")

            user = None
            max_username_attempts = 5
            for _ in range(max_username_attempts):
                try:
                    user = User.objects.create_user(
                        email=email,
                        password=password,
                        username=_build_random_bureau_username(),
                        role="user",
                        status="active",
                        is_active=True,
                    )
                    break
                except IntegrityError:
                    # Convergence under concurrency:
                    # if competing request already created this email, fail safely.
                    if _email_exists_ci(User, email):
                        raise ValidationError("An account with this email already exists.")
                    # Rare username collision: retry with a new random username.
                    continue

            if user is None:
                raise ValidationError("Registration failed. Please try again.")

            # Defensive safety even with OneToOne relation.
            if BureauProfile.objects.select_for_update().filter(user=user).exists():
                raise ValidationError("A bureau profile already exists for this account.")

            BureauProfile.objects.create(
                user=user,
                bureau_name=bureau_name,
                phone_number=phone_number,
                address=address,
                city=city,
                whatsapp_number=whatsapp_number,
                is_active=False,
                is_approved=False,
                is_email_verified=False,
            )
            from otp_verification.registration.completions import (
                _sync_expert_user_phone,
                mark_bureau_user_phone_verified,
            )

            _sync_expert_user_phone(user, phone_number)
    except (ValidationError, IntegrityError):
        messages.error(request, "Registration failed. Please try again.")
        return render(
            request,
            "bureaus/register.html",
            {"form_data": form_data},
            status=400,
        )
    except Exception:
        messages.error(request, "Registration failed. Please try again.")
        return render(
            request,
            "bureaus/register.html",
            {"form_data": form_data},
            status=500,
        )

    try:
        from accounts.email_verification import create_email_verification

        create_email_verification(user)
    except Exception:
        logger.exception(
            "Failed to create email verification after bureau registration"
        )

    messages.success(request, "Registration successful. Awaiting admin approval.")
    from otp_verification.registration.completions import mark_bureau_user_phone_verified
    from otp_verification.registration.session import (
        consume_phone_verified_session,
        phone_verified_matches_registration,
    )

    if phone_verified_matches_registration(
        request,
        flow_type=otp_constants.FLOW_BUREAU_REGISTRATION,
        destination=phone_number,
    ):
        mark_bureau_user_phone_verified(email=email, phone=phone_number)
    consume_phone_verified_session(request)
    return render(request, "bureaus/register.html", status=201)


def _slug_to_city_needle(city_slug):
    return (city_slug or "").replace("-", " ").strip()


def _slug_to_city_display(city_slug):
    return _slug_to_city_needle(city_slug).title()


@require_http_methods(["GET"])
def bureau_city_view(request, city):
    """
    Public city landing page for bureaus (SEO). Uses same visibility rules as bureau list.
    """
    needle = _slug_to_city_needle(city)
    qs = get_visible_bureaus_queryset().order_by("-created_at", "-id")
    if needle:
        bureaus = qs.filter(city__icontains=needle)
    else:
        bureaus = qs.none()
    return render(
        request,
        "bureaus/city.html",
        {
            "bureaus": bureaus,
            "city": _slug_to_city_display(city),
        },
    )
