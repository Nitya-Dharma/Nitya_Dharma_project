from django.shortcuts import get_object_or_404, render
from django.db.models import F
from core.models import ExpertProfile, ExpertReview, ExpertInquiry
from .models import ExpertBookingIntent


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
    expert = get_object_or_404(ExpertProfile, id=id)
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
