"""
Phase-3 analytics protections: bot filtering, rate limiting, request validation,
and backend duplicate-impression guard. Does not change endpoint URLs or HTTP methods.
"""

import logging
import re
import time
from typing import Optional, Tuple

from django.http import HttpRequest

logger = logging.getLogger(__name__)

# Known crawler/bot User-Agent substrings (case-insensitive). Legitimate browsers are not matched.
BOT_UA_PATTERNS = [
    r"googlebot",
    r"bingbot",
    r"slurp",           # Yahoo
    r"duckduckbot",
    r"baiduspider",
    r"yandexbot",
    r"facebookexternalhit",
    r"twitterbot",
    r"rogerbot",
    r"linkedinbot",
    r"embedly",
    r"quora link preview",
    r"showyoubot",
    r"outbrain",
    r"pinterest",
    r"slackbot",
    r"vkshare",
    r"w3c_validator",
    r"redditbot",
    r"applebot",
    r"whatsapp",
    r"flipboard",
    r"tumblr",
    r"bitlybot",
    r"skypeuripreview",
    r"nuzzel",
    r"discordbot",
    r"qwantify",
    r"pinterestbot",
    r"bitrix link preview",
    r"xing-contenttabreceiver",
    r"chrome-lighthouse",
    r"telegrambot",
    r"petalbot",
    r"ahrefsbot",
    r"semrushbot",
    r"dotbot",
    r"mj12bot",
    r"bytespider",      # ByteDance
]
BOT_UA_REGEX = re.compile("|".join(f"({p})" for p in BOT_UA_PATTERNS), re.I)

# Rate limit: max requests per key per window (per endpoint type)
RATE_LIMIT_IMPRESSION_WINDOW_SEC = 60
RATE_LIMIT_IMPRESSION_MAX = 120   # per IP per minute (allows normal browsing with many ads)
RATE_LIMIT_CLICK_WINDOW_SEC = 60
RATE_LIMIT_CLICK_MAX = 60

# Duplicate impression: ignore same ad + same client within this many seconds
DUPLICATE_IMPRESSION_WINDOW_SEC = 2

# Placement: allow only alphanumeric, underscore, hyphen; max length from model
PLACEMENT_MAX_LENGTH = 50
PLACEMENT_VALID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{0,50}$")


def _get_client_key(request: HttpRequest) -> str:
    """Stable key for rate limit and duplicate check (IP + optional session)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        ip = xff.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "unknown")
    session = getattr(request, "session", None)
    if session and session.session_key:
        return f"{ip}:{session.session_key}"
    return ip


def _cache_get(cache, key: str):
    try:
        return cache.get(key)
    except Exception:
        return None


def _cache_set(cache, key: str, value, timeout: int):
    try:
        cache.set(key, value, timeout=timeout)
    except Exception:
        pass


def _cache_incr(cache, key: str, timeout: int) -> int:
    """Increment counter; return new value. Creates key at 1 if missing."""
    try:
        val = cache.get(key)
        if val is None:
            cache.set(key, 1, timeout=timeout)
            return 1
        cache.incr(key)
        return val + 1
    except Exception:
        return 1


def is_bot_request(request: HttpRequest) -> bool:
    """
    True if request appears to be from a known crawler/bot.
    Legitimate browsers (Chrome, Firefox, Safari, Edge, etc.) return False.
    """
    ua = request.META.get("HTTP_USER_AGENT") or ""
    if not ua.strip():
        # Empty UA is suspicious; could be script. Allow for now to avoid blocking legacy clients.
        return False
    return bool(BOT_UA_REGEX.search(ua))


def is_rate_limited_impression(request: HttpRequest) -> bool:
    """True if this IP (and session) has exceeded impression rate limit."""
    try:
        from django.core.cache import cache
    except ImportError:
        return False
    key = f"ads_analytics:rate:imp:{_get_client_key(request)}"
    count = _cache_incr(cache, key, RATE_LIMIT_IMPRESSION_WINDOW_SEC)
    return count > RATE_LIMIT_IMPRESSION_MAX


def is_rate_limited_click(request: HttpRequest) -> bool:
    """True if this IP (and session) has exceeded click rate limit."""
    try:
        from django.core.cache import cache
    except ImportError:
        return False
    key = f"ads_analytics:rate:click:{_get_client_key(request)}"
    count = _cache_incr(cache, key, RATE_LIMIT_CLICK_WINDOW_SEC)
    return count > RATE_LIMIT_CLICK_MAX


def validate_placement(placement: str) -> bool:
    """Placement must be safe string and within length."""
    if placement is None:
        return True
    if len(placement) > PLACEMENT_MAX_LENGTH:
        return False
    return bool(PLACEMENT_VALID_PATTERN.match(placement))


def is_duplicate_impression(ad_id: int, request: HttpRequest) -> bool:
    """
    True if we already recorded an impression for this ad from this client
    within the last DUPLICATE_IMPRESSION_WINDOW_SEC seconds (backend guard).
    """
    try:
        from django.core.cache import cache
    except ImportError:
        return False
    client = _get_client_key(request)
    key = f"ads_analytics:dup_imp:{ad_id}:{client}"
    now = time.time()
    existing = _cache_get(cache, key)
    if existing is not None and (now - float(existing)) < DUPLICATE_IMPRESSION_WINDOW_SEC:
        return True
    _cache_set(cache, key, str(now), timeout=DUPLICATE_IMPRESSION_WINDOW_SEC + 1)
    return False


def should_skip_tracking(
    request: HttpRequest,
    ad_id: int,
    placement: str,
    *,
    is_impression: bool,
) -> Tuple[bool, Optional[str]]:
    """
    Returns (skip, reason). skip=True means do not record the event; still return normal HTTP response.
    """
    if is_bot_request(request):
        return True, "bot"
    if is_impression:
        if is_rate_limited_impression(request):
            return True, "rate_limit"
        if is_duplicate_impression(ad_id, request):
            return True, "duplicate_impression"
    else:
        if is_rate_limited_click(request):
            return True, "rate_limit"
    if not validate_placement(placement or ""):
        return True, "invalid_placement"
    return False, None
