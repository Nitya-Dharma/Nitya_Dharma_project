from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import F
from django.db import transaction
from core.models import ExpertProfile, ExpertReview, ExpertInquiry, ExpertService

from .expert_service_selection import (
    ExpertServiceSelectionError,
    primary_expert_type,
    resolve_active_services_by_ids,
    service_slugs,
)
from .models import ExpertBookingIntent, ExpertSocialLink

User = get_user_model()

VALID_TYPES = ["astrologer", "numerologist", "palmist"]


def _absolute_site_url(view_name, *args, **kwargs):
    """Build absolute URL using SITE_URL + reverse (same pattern as Pandit email)."""
    site_url = getattr(settings, "SITE_URL", None)
    if not site_url:
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
        if allowed_hosts and allowed_hosts[0] != "*":
            host = allowed_hosts[0]
        else:
            host = "127.0.0.1:8000"
        protocol = "https" if getattr(settings, "USE_HTTPS", False) else "http"
        site_url = f"{protocol}://{host}"
    site_url = site_url.rstrip("/")
    relative_path = reverse(view_name, args=args, **kwargs)
    if not relative_path.startswith("/"):
        relative_path = "/" + relative_path
    return f"{site_url}{relative_path}"


def _redirect_expert_register(request):
    url = reverse("expert_register")
    if request.GET:
        url = f"{url}?{request.GET.urlencode()}"
    return redirect(url)

def become_expert_home(request):
    """
    Thin landing only. Does NOT create ExpertProfile/User/OTP.
    Canonical registration remains the sole Expert creation lifecycle.
    """
    if request.method == "POST":
        # Neutralize legacy WIP create: never write ExpertProfile here.
        return redirect(reverse("expert_register"))

    return render(
        request,
        "expert/become_expert.html",
        {
            "expert_register_url": reverse("expert_register"),
        },
    )


def expert_type_page(request, expert_type):
    """
    Entry helper into canonical register. Does NOT create ExpertProfile.
    Uses existing expert_register ?type= preselect (already supported).
    """
    if expert_type not in VALID_TYPES:
        return render(request, "expert/invalid_type.html")

    return redirect(
        f"{reverse('expert_register')}?type={expert_type}"
    )


def expert_register_page(request):
    expert_type = request.GET.get("type")
    error = None
    available_services = list(
        ExpertService.objects.filter(is_active=True).order_by("display_order", "name")
    )
    selected_service_ids = []
    preselected_slug = {
        "astrology": "astrology",
        "astrologer": "astrology",
        "numerology": "numerology",
        "numerologist": "numerology",
        "palmistry": "palmistry",
        "palmist": "palmistry",
    }.get((expert_type or "").lower())
    if preselected_slug:
        selected_service_ids = [
            service.id
            for service in available_services
            if service.slug == preselected_slug
        ]

    if request.method == "POST":
        try:
            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")
            confirm_password = request.POST.get("confirm_password")
            phone = request.POST.get("phone")
            experience_years = request.POST.get("experience_years")
            description = request.POST.get("description")
            selected_service_ids = request.POST.getlist("services")
            social_links_raw = request.POST.getlist("social_links[]")
            social_links = [link.strip() for link in social_links_raw if link.strip()]
            social_links = list(
                dict.fromkeys([link.strip() for link in social_links if link.strip()])
            )

            normalized_links = []
            for link in social_links:
                link = link.strip()

                if not link.startswith("http://") and not link.startswith(
                    "https://"
                ):
                    link = "https://" + link

                normalized_links.append(link)

            social_links = normalized_links

            existing = None
            existing_email = None

            selected_services = []
            normalized_type = None
            try:
                selected_services = resolve_active_services_by_ids(
                    selected_service_ids
                )
                normalized_type = primary_expert_type(selected_services)
                selected_service_ids = [
                    service.id for service in selected_services
                ]
            except ExpertServiceSelectionError as exc:
                error = str(exc)

            if not name or not phone or not normalized_type:
                if not error:
                    error = "Please fill all required fields."
            elif not email:
                error = "Email is required."
            elif not password or not confirm_password:
                error = "Password is required."
            elif password != confirm_password:
                error = "Passwords do not match."
            elif not phone.isdigit() or len(phone) < 8:
                error = "Enter a valid phone number."
            else:
                try:
                    experience_years = int(experience_years)
                    if experience_years < 0:
                        error = "Experience must be a positive number."
                except Exception:
                    error = "Invalid experience value."

            if not error:
                existing = ExpertProfile.objects.filter(
                    phone=phone,
                ).first()
                if email:
                    existing_email = ExpertProfile.objects.filter(
                        email=email
                    ).first()

                if existing or existing_email:
                    error = "An account with this phone or email already exists."

            if not error:
                if not social_links:
                    messages.error(
                        request,
                        "Please add at least one social profile link.",
                    )
                    return _redirect_expert_register(request)
                url_validator = URLValidator()
                for link in social_links:
                    try:
                        url_validator(link)
                    except ValidationError:
                        messages.error(
                            request,
                            "Please enter valid URLs for social profile links.",
                        )
                        return _redirect_expert_register(request)

            if not error and not existing and not existing_email:
                from otp_verification import constants as otp_constants
                from otp_verification.registration.factory import is_registration_otp_required
                from otp_verification.registration.gate import begin_otp_or_continue

                if is_registration_otp_required(otp_constants.FLOW_EXPERT_REGISTRATION):
                    otp_response = begin_otp_or_continue(
                        request,
                        flow_type=otp_constants.FLOW_EXPERT_REGISTRATION,
                        destination=phone,
                        payload={
                            "name": name,
                            "email": email,
                            "password": password,
                            "phone": phone,
                            "experience_years": experience_years,
                            "description": description,
                            "expert_type": normalized_type,
                            "service_slugs": service_slugs(selected_services),
                            "social_links": social_links,
                        },
                        resume_path="/services/expert/register/",
                    )
                    if otp_response is not None:
                        if otp_response.status_code == 400:
                            error = "Unable to start phone verification. Please check your phone number."
                        else:
                            return otp_response

            if not error and not existing and not existing_email:
                user = None

                with transaction.atomic():
                    if email:
                        user = User.objects.filter(email__iexact=email).first()

                        if not user:
                            user = User.objects.create_user(
                                username=email,
                                email=email,
                                password=password
                            )
                            if user:
                                try:
                                    send_mail(
                                        subject="Set Your Password",
                                        message=(
                                            "Your expert account has been created.\n\n"
                                            "Please reset your password here:\n"
                                            f"{_absolute_site_url('accounts:password_reset')}"
                                        ),
                                        from_email=settings.DEFAULT_FROM_EMAIL,
                                        recipient_list=[email],
                                        fail_silently=True,
                                    )
                                except Exception:
                                    pass

                with transaction.atomic():
                    expert = ExpertProfile.objects.create(
                        name=name,
                        email=email,
                        phone=phone,
                        experience_years=experience_years,
                        description=description,
                        expert_type=normalized_type,
                        is_active=False,
                        is_verified=False,
                    )
                    expert.services.set(selected_services)

                    for link in social_links:
                        ExpertSocialLink.objects.create(expert=expert, url=link)

                try:
                    send_mail(
                        subject="New Expert Registration",
                        message=f"A new expert has registered.\n\nName: {name}\nPhone: {phone}\nType: {normalized_type}",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[settings.DEFAULT_FROM_EMAIL],
                        fail_silently=True,
                    )
                except Exception:
                    pass

                from otp_verification.registration.session import consume_phone_verified_session
                consume_phone_verified_session(request)
                return render(
                    request,
                    "expert/register.html",
                    {
                        "expert_type": expert_type,
                        "available_services": available_services,
                        "selected_service_ids": selected_service_ids,
                        "success": True,
                        "error": None,
                    },
                )

        except Exception:
            pass

    return render(
        request,
        "expert/register.html",
        {
            "expert_type": expert_type,
            "error": error,
            "available_services": available_services,
            "selected_service_ids": selected_service_ids,
        },
    )

def expert_pending_page(request):
    return render(request, "expert/pending.html")


def get_expert_by_user(user):
    from core.models import ExpertProfile

    if not user.is_authenticated:
        return None

    try:
        return ExpertProfile.objects.filter(
            email__iexact=user.email,
            is_active=True
        ).first()
    except Exception:
        return None

def expert_profile_page(request, id):
    # Public detail must match listing/discovery: only active Experts are exposed.
    expert = get_object_or_404(ExpertProfile, id=id, is_active=True)
    ExpertProfile.objects.filter(id=expert.id).update(
        profile_views=F("profile_views") + 1
    )
    expert.refresh_from_db(fields=["profile_views"])
    success = False
    contact_success = False
    reviewed_experts = request.session.get("reviewed_experts", [])

    # Pending intent for this expert only (not global per user).
    has_active_intent = False
    if request.user.is_authenticated:
        has_active_intent = ExpertBookingIntent.objects.filter(
            expert=expert,
            user=request.user,
            is_viewed=False,
        ).exists()

    if request.method == "POST":
        if request.POST.get("phone"):
            name = request.POST.get("name")
            phone = request.POST.get("phone")
            message = request.POST.get("message")

            try:
                if not name:
                    raise ValueError

                if not phone or not phone.isdigit() or len(phone) < 8:
                    raise ValueError

                ExpertInquiry.objects.create(
                    expert=expert,
                    name=name,
                    phone=phone,
                    message=message or "",
                )
                contact_success = True

                # Shared Notification for Expert owner (same pattern as booking intent).
                # Must not fail the successful inquiry submission.
                expert_owner = None
                if expert.email:
                    expert_owner = User.objects.filter(
                        email__iexact=expert.email
                    ).first()
                if expert_owner is not None:
                    try:
                        from notifications.constants import (
                            NOTIFICATION_TYPE_BOOKING_INTENT,
                        )
                        from notifications.services import NotificationService

                        NotificationService.create_notification(
                            recipient=expert_owner,
                            notification_type=NOTIFICATION_TYPE_BOOKING_INTENT,
                            source_module="services",
                            payload={
                                "title": "New inquiry",
                                "message": (
                                    "You received a new inquiry on your expert profile."
                                ),
                                "url": "/dashboard/expert/?tab=requests",
                            },
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        if str(expert.id) in reviewed_experts:
            pass
        else:
            try:
                rating = int(rating)

                if rating < 1 or rating > 5:
                    raise ValueError

                ExpertReview.objects.create(
                    expert=expert,
                    rating=rating,
                    comment=comment or "",
                )

                reviewed_experts.append(str(expert.id))
                request.session["reviewed_experts"] = reviewed_experts

                success = True
            except Exception:
                pass

    reviews = expert.reviews.all().order_by("-created_at")

    return render(
        request,
        "services/expert_profile.html",
        {
            "expert": expert,
            "reviews": reviews,
            "success": success,
            "contact_success": contact_success,
            "has_active_intent": has_active_intent,
            "invalid_id": None,
        },
    )
