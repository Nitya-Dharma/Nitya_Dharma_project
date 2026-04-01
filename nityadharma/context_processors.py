"""
Project-level context processors.
"""
from masterdata.models import Pooja, PoojaCategory


def pooja_data(request):
    """
    Provide global pooja data for navbar dropdowns across all pages.
    """
    poojas = list(
        Pooja.objects.filter(
            is_active=True,
            status=Pooja.STATUS_ACTIVE,
            pooja_category__isnull=False,
            pooja_category__is_active=True,
            pooja_category__status=PoojaCategory.STATUS_ACTIVE,
        )
        .select_related("pooja_category")
        .order_by("pooja_category__display_order", "pooja_category__name", "name")
    )

    grouped = {}
    for pooja in poojas:
        category_name = pooja.pooja_category.name
        grouped.setdefault(category_name, []).append(pooja)

    return {
        "navbar_pooja_categories": grouped,
        "navbar_poojas": poojas,
    }
