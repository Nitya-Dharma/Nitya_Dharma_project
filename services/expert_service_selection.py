"""Validation and compatibility helpers for Expert service selection."""

from __future__ import annotations

from collections.abc import Iterable

from core.models import ExpertService


class ExpertServiceSelectionError(ValueError):
    """Raised when submitted Expert services are missing or invalid."""


SERVICE_PRIORITY = ("astrology", "numerology", "palmistry")
EXPERT_TYPE_BY_SLUG = {
    "astrology": "ASTROLOGER",
    "numerology": "NUMEROLOGIST",
    "palmistry": "PALMIST",
}
_PRIORITY_INDEX = {slug: index for index, slug in enumerate(SERVICE_PRIORITY)}


def _ordered_services(services: Iterable[ExpertService]) -> list[ExpertService]:
    resolved = list(services)
    if not resolved:
        raise ExpertServiceSelectionError("Please select at least one service.")
    if any(service.slug not in _PRIORITY_INDEX for service in resolved):
        raise ExpertServiceSelectionError("Please select valid active services.")
    return sorted(resolved, key=lambda service: _PRIORITY_INDEX[service.slug])


def resolve_active_services_by_ids(raw_ids: Iterable[object]) -> list[ExpertService]:
    """Strictly resolve browser-submitted IDs to active supported services."""
    submitted: set[int] = set()
    for raw_id in raw_ids:
        text = str(raw_id).strip()
        if not text.isdigit() or int(text) <= 0:
            raise ExpertServiceSelectionError("Please select valid active services.")
        submitted.add(int(text))

    if not submitted:
        raise ExpertServiceSelectionError("Please select at least one service.")

    services = list(
        ExpertService.objects.filter(id__in=submitted, is_active=True)
    )
    if {service.id for service in services} != submitted:
        raise ExpertServiceSelectionError("Please select valid active services.")
    return _ordered_services(services)


def resolve_active_services_by_slugs(raw_slugs: Iterable[object]) -> list[ExpertService]:
    """Strictly resolve OTP payload slugs to active supported services."""
    submitted = {str(raw_slug).strip().lower() for raw_slug in raw_slugs}
    if not submitted or "" in submitted:
        raise ExpertServiceSelectionError("Please select at least one service.")
    if not submitted.issubset(EXPERT_TYPE_BY_SLUG):
        raise ExpertServiceSelectionError("Please select valid active services.")

    services = list(
        ExpertService.objects.filter(slug__in=submitted, is_active=True)
    )
    if {service.slug for service in services} != submitted:
        raise ExpertServiceSelectionError("Please select valid active services.")
    return _ordered_services(services)


def primary_expert_type(services: Iterable[ExpertService]) -> str:
    """Return the legacy expert_type for the highest-priority service."""
    ordered = _ordered_services(services)
    return EXPERT_TYPE_BY_SLUG[ordered[0].slug]


def service_slugs(services: Iterable[ExpertService]) -> list[str]:
    """Return validated service slugs in deterministic priority order."""
    return [service.slug for service in _ordered_services(services)]
