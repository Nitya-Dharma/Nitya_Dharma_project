# Re-export event recording (used by views and templatetags) and dashboard service.
from .event_recording import (
    record_ad_impression,
    record_ad_click,
    record_ad_conversion_intent,
    record_ad_revenue_event,
)
from .attribution_bridge import (
    store_last_click_attribution,
    record_booking_conversion_from_session,
    record_whatsapp_contact_from_session,
)
