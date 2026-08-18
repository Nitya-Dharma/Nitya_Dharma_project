import logging

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Avg, Prefetch
from django.shortcuts import render

from core.models import ExpertService

from .expert_discovery import experts_offering

logger = logging.getLogger(__name__)


def palmistry_service_view(request):
    experts = []
    featured_experts = []
    error_message = None
    min_exp = request.GET.get("min_exp")
    search = request.GET.get("q")
    sort = request.GET.get("sort")

    try:
        active_services = Prefetch(
            "services",
            queryset=ExpertService.objects.filter(is_active=True),
            to_attr="active_services",
        )
        experts = (
            experts_offering("palmistry")
            .annotate(avg_rating=Avg("reviews__rating"))
            .prefetch_related(active_services)
        )
        featured_experts = (
            experts_offering("palmistry")
            .order_by("-experience_years")
        )[:3]
        if min_exp:
            try:
                experts = experts.filter(
                    experience_years__gte=int(min_exp)
                )
            except Exception:
                pass

        if search:
            experts = experts.filter(name__icontains=search)
        if sort == "exp_desc":
            experts = experts.order_by("-experience_years")
        elif sort == "exp_asc":
            experts = experts.order_by("experience_years")

        paginator = Paginator(experts, 6)
        page_number = request.GET.get("page")
        experts = paginator.get_page(page_number)
    except Exception as e:
        # Log error (safe, does not break system)
        logger.warning("Palmistry service fallback triggered: %s", str(e))

        # Only expose error in DEBUG mode
        if settings.DEBUG:
            error_message = str(e)

        # Model may not exist yet — keep system safe
        experts = []

    return render(
        request,
        "services/palmistry.html",
        {
            "experts": experts,
            "featured_experts": featured_experts,
            "debug_error": error_message,
        },
    )
