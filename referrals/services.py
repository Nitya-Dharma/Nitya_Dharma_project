"""
Referral link creation and revocation service layer.

Single source of truth for referral creation and revoke logic.
Used by both Admin Pandit (JSON API) and Super Admin (dashboard UI).
No business logic duplication; policy and validation live here only.
"""
import secrets
from datetime import timedelta

from django.utils import timezone

from .models import ReferralLink, ReferralPolicy


def _generate_unique_token():
    """Generate a unique, URL-safe token for referral link."""
    return secrets.token_hex(32)


def get_expiry_days_options(policy):
    """
    Derive expiry day options from ReferralPolicy (no hardcoded literals).
    Returns sorted list of allowed expiry days for dropdowns.
    """
    if not policy:
        return []
    default_d = policy.default_expiry_days
    max_d = policy.max_allowed_expiry_days
    step = max(1, max_d // 10)
    options = sorted(set([default_d, max_d] + list(range(1, max_d + 1, step))))
    return [d for d in options if 1 <= d <= max_d]


def create_referral_link(creator, max_uses, expiry_days):
    """
    Create a new referral link respecting ReferralPolicy.

    Args:
        creator: User instance (Admin Pandit or Super Admin).
        max_uses: int, must be in policy.allowed_max_use_tiers and <= policy.max_allowed_uses.
        expiry_days: int, must be 1 <= expiry_days <= policy.max_allowed_expiry_days.

    Returns:
        ReferralLink: the created instance.

    Raises:
        ValueError: if max_uses or expiry_days are invalid per policy.
    """
    policy = ReferralPolicy.load()
    tiers = list(policy.allowed_max_use_tiers) if isinstance(policy.allowed_max_use_tiers, (list, tuple)) else []
    if not tiers:
        tiers = [min(policy.max_allowed_uses, 100)]
    try:
        max_uses = int(max_uses)
    except (TypeError, ValueError):
        raise ValueError(f"max_uses must be one of: {tiers}. Hard cap: {policy.max_allowed_uses}.")
    if max_uses not in tiers or max_uses > policy.max_allowed_uses:
        raise ValueError(f"max_uses must be one of the allowed tiers: {tiers}. Cannot exceed {policy.max_allowed_uses}.")
    try:
        expiry_days = int(expiry_days)
    except (TypeError, ValueError):
        expiry_days = policy.default_expiry_days
    if expiry_days < 1 or expiry_days > policy.max_allowed_expiry_days:
        expiry_days = min(max(1, expiry_days), policy.max_allowed_expiry_days)

    token = _generate_unique_token()
    referral_code = token
    max_retries = 5
    for attempt in range(max_retries):
        if not ReferralLink.objects.filter(token=token).exists():
            break
        if attempt < max_retries - 1:
            token = _generate_unique_token()
            referral_code = token
        else:
            raise ValueError("Unable to generate unique referral token. Please try again.")

    expires_at = timezone.now() + timedelta(days=expiry_days)
    referrer_status = getattr(creator, 'status', None) or 'active'
    referrer_block_state = 'none'

    return ReferralLink.objects.create(
        created_by=creator,
        token=token,
        referral_code=referral_code,
        max_uses=max_uses,
        used_count=0,
        is_active=True,
        expires_at=expires_at,
        status=ReferralLink.STATUS_ACTIVE,
        referrer_status_at_creation=referrer_status,
        referrer_block_state_at_creation=referrer_block_state,
    )


def revoke_referral_link(referral_link_id, actor):
    """
    Revoke (deactivate) a referral link. Same behavior as Admin Pandit deactivate.

    Args:
        referral_link_id: int, ReferralLink.pk.
        actor: User instance (must be Admin Pandit or Super Admin).

    Returns:
        ReferralLink: the updated instance.

    Raises:
        PermissionDenied: if actor cannot manage referral links.
        ReferralLink.DoesNotExist: if link not found.
    """
    from accounts.utils import is_admin
    from django.core.exceptions import PermissionDenied

    if not actor or not actor.is_authenticated:
        raise PermissionDenied("Authentication required")
    if not actor.is_superuser and not (is_admin(actor) and getattr(actor, 'status', None) == 'active' and actor.is_active):
        raise PermissionDenied("Only Admin Pandits (active) and Super Admins can manage referral links.")

    link = ReferralLink.objects.get(id=referral_link_id)
    if not link.is_active:
        raise ValueError("Referral link is already inactive")
    link.is_active = False
    link.status = ReferralLink.STATUS_REVOKED
    link.save(update_fields=['is_active', 'status', 'updated_at'])
    return link
