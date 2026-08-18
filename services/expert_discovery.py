"""Read-only queryset helpers for Expert service discovery."""

from core.models import ExpertProfile


SUPPORTED_SERVICE_SLUGS = frozenset({"astrology", "numerology", "palmistry"})


def filter_experts_offering(experts, service_slug: str):
    """Filter an existing ExpertProfile queryset by active service membership."""
    normalized_slug = (service_slug or "").strip().lower()
    if normalized_slug not in SUPPORTED_SERVICE_SLUGS:
        raise ValueError("Unsupported expert service slug.")
    return experts.filter(
        services__slug=normalized_slug,
        services__is_active=True,
    ).distinct()


def experts_offering(
    service_slug: str,
    *,
    active_experts_only: bool = True,
):
    """Return experts offering an active, supported service."""
    experts = ExpertProfile.objects.all()
    if active_experts_only:
        experts = experts.filter(is_active=True)
    return filter_experts_offering(experts, service_slug)
