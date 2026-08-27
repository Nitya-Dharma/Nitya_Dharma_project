from django.core.exceptions import PermissionDenied

from .models import BureauProfile


def get_visible_bureaus():
    return BureauProfile.objects.filter(
        is_active=True,
        is_approved=True,
        is_email_verified=True,
    )


def is_profile_complete_for_listing(profile):
    return all([
        profile.description,
        profile.phone_number,
        profile.address,
        profile.city,
        profile.caste_data,
    ])


def get_homepage_bureaus():
    qs = get_visible_bureaus()
    return [b for b in qs if is_profile_complete_for_listing(b)][:3]


def get_bureau_for_user(user):
    try:
        return BureauProfile.objects.get(
            user=user,
            is_active=True,
            is_approved=True,
            is_email_verified=True,
        )
    except BureauProfile.DoesNotExist:
        return None


def get_bureau_by_user_or_404(user):
    bureau = get_bureau_for_user(user)
    if not bureau:
        raise PermissionDenied("Unauthorized bureau access")
    return bureau


def assert_bureau_object(obj):
    assert isinstance(obj, BureauProfile), "Invalid bureau object"
