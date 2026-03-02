"""
Referral tier analytics — read-only aggregation for Super Admin dashboard.
No writes; no modification of referral links. Used by Behavior Analytics dashboard.
"""

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

# Default thresholds when settings are missing
_DEFAULT_HIGH_TIER_100_THRESHOLD = 10
_DEFAULT_HIGH_TIER_50_THRESHOLD = 20


def get_referral_tier_analytics():
    """
    Return read-only KPIs: tier distribution, usage rate per tier,
    expiry rate per tier, links per admin, high-tier usage.
    """
    from .models import ReferralLink

    qs = ReferralLink.objects.all()
    now = timezone.now()

    # Tier distribution: count of links per max_uses
    tier_distribution = list(
        qs.values('max_uses')
        .annotate(count=Count('id'))
        .order_by('max_uses')
    )
    # Normalize to list of {tier, count}
    tier_distribution = [{'tier': x['max_uses'], 'count': x['count']} for x in tier_distribution]

    # Usage rate per tier: for each tier, total links and total used_count
    usage_by_tier = []
    for row in tier_distribution:
        tier = row['tier']
        links = qs.filter(max_uses=tier)
        total_links = links.count()
        total_slots = total_links * tier if total_links else 0
        used_sum = links.aggregate(s=Sum('used_count'))['s'] or 0
        usage_pct = round(100 * used_sum / total_slots, 1) if total_slots else 0
        usage_by_tier.append({
            'tier': tier,
            'total_links': total_links,
            'total_used': used_sum,
            'usage_rate_pct': usage_pct,
        })

    # Expiry rate per tier: count expired (status=expired or expires_at < now) per tier
    expired_qs = qs.filter(Q(status=ReferralLink.STATUS_EXPIRED) | Q(expires_at__lt=now))
    expiry_by_tier = list(
        expired_qs.values('max_uses')
        .annotate(count=Count('id'))
        .order_by('max_uses')
    )
    expiry_by_tier = [{'tier': x['max_uses'], 'expired_count': x['count']} for x in expiry_by_tier]

    # Links generated per admin (created_by)
    links_per_admin = list(
        qs.values('created_by__email', 'created_by__id')
        .annotate(count=Count('id'))
        .order_by('-count')[:20]
    )
    links_per_admin = [
        {'admin_email': x['created_by__email'] or '—', 'admin_id': x['created_by__id'], 'count': x['count']}
        for x in links_per_admin
    ]

    # High-tier usage: count of 50- and 100-use links
    from core.config import get_config_value
    high_tier_50 = qs.filter(max_uses=50).count()
    high_tier_100 = qs.filter(max_uses=100).count()
    settings_100 = getattr(settings, 'REFERRAL_HIGH_TIER_100_ALERT_THRESHOLD', _DEFAULT_HIGH_TIER_100_THRESHOLD)
    settings_50 = getattr(settings, 'REFERRAL_HIGH_TIER_50_ALERT_THRESHOLD', _DEFAULT_HIGH_TIER_50_THRESHOLD)
    thresh_100 = get_config_value('REFERRAL_HIGH_TIER_100_ALERT_THRESHOLD', settings_100)
    thresh_50 = get_config_value('REFERRAL_HIGH_TIER_50_ALERT_THRESHOLD', settings_50)
    high_tier_alerts = []
    if high_tier_100 > thresh_100:
        high_tier_alerts.append(f'{high_tier_100} links with 100-use tier')
    if high_tier_50 > thresh_50:
        high_tier_alerts.append(f'{high_tier_50} links with 50-use tier')

    return {
        'tier_distribution': tier_distribution,
        'usage_by_tier': usage_by_tier,
        'expiry_by_tier': expiry_by_tier,
        'links_per_admin': links_per_admin,
        'high_tier_50_count': high_tier_50,
        'high_tier_100_count': high_tier_100,
        'high_tier_alerts': high_tier_alerts,
    }
