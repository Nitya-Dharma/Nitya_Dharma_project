"""
Create AdLead records from already-persisted AdConversionIntent events.

Does not record analytics, attribution, WhatsApp, or booking side effects.
"""

from django.db import IntegrityError, transaction

from ads_analytics.models import AdLead

_VALID_SOURCES = frozenset(
    {
        AdLead.SOURCE_WHATSAPP_CTA,
        AdLead.SOURCE_BOOKING_INTENT,
    }
)


def create_ad_lead_from_conversion(conversion, source):
    """
    Return the AdLead for this conversion, creating it if needed.

    Identity is one Lead per AdConversionIntent. Does not deduplicate on
    advertisement, user, or anonymous visitor attributes.
    """
    existing = AdLead.objects.filter(source_conversion=conversion).first()
    if existing is not None:
        return existing

    if source not in _VALID_SOURCES:
        raise ValueError(f"Unsupported AdLead source: {source!r}")

    try:
        with transaction.atomic():
            return AdLead.objects.create(
                source_conversion=conversion,
                advertisement_id=conversion.ad_id,
                campaign_id=conversion.campaign_id,
                user_id=conversion.user_id,
                source=source,
                status=AdLead.STATUS_NEW,
            )
    except IntegrityError:
        return AdLead.objects.get(source_conversion=conversion)
