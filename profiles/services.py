from collections import OrderedDict
from typing import Dict, List, Tuple, Any

from masterdata.models import City


def group_poojas_by_category_for_profile(all_poojas) -> "OrderedDict[str, List[Any]]":
    """
    Group poojas into pooja_categories for Pandit profile editing UI.

    This function preserves the existing behavior (including legacy fallback)
    and returns the same OrderedDict structure the template expects.
    """
    pooja_categories = OrderedDict()

    for pooja in all_poojas:
        if pooja.pooja_category and pooja.pooja_category.is_active:
            category_name = pooja.pooja_category.name
            if category_name not in pooja_categories:
                pooja_categories[category_name] = []
            pooja_categories[category_name].append(pooja)
        elif pooja.category:
            # Fallback: Use deprecated category enum if pooja_category FK is not set
            category_display = pooja.get_category_display()
            if category_display not in pooja_categories:
                pooja_categories[category_display] = []
            pooja_categories[category_display].append(pooja)
        else:
            # Fallback for poojas without any category
            fallback_category = "Uncategorized"
            if fallback_category not in pooja_categories:
                pooja_categories[fallback_category] = []
            pooja_categories[fallback_category].append(pooja)

    return pooja_categories


def get_available_states_and_preselected_state(profile) -> Tuple[List[str], str | None]:
    """
    Build State dropdown data for Pandit profile editing UI.

    Preserves existing query, ordering, and fallback list behavior.
    """
    available_states = list(
        City.objects.filter(is_active=True)
        .exclude(state__isnull=True)
        .exclude(state="")
        .values_list("state", flat=True)
        .distinct()
        .order_by("state")
    )

    if not available_states:
        available_states = [
            "Andhra Pradesh",
            "Bihar",
            "Delhi",
            "Goa",
            "Gujarat",
            "Karnataka",
            "Kerala",
            "Madhya Pradesh",
            "Maharashtra",
            "Punjab",
            "Rajasthan",
            "Tamil Nadu",
            "Telangana",
            "Uttar Pradesh",
            "West Bengal",
        ]

    preselected_state = None
    if profile.pk:
        first_city = profile.cities_served.first()
        if first_city and (first_city.state or "").strip():
            preselected_state = first_city.state.strip()

        # Ensure states from the user's selected cities are present in the dropdown,
        # even if those cities are pending/inactive (e.g., created via "Others").
        selected_states = list(
            profile.cities_served.values_list("state", flat=True).distinct()
        )
        for st in selected_states:
            if st and str(st).strip() and st.strip() not in available_states:
                available_states.append(st.strip())

    return available_states, preselected_state

