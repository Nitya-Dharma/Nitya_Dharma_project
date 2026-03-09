"""
Search Service

Task 7.13: Search Query Logic
Task 7.15: Search Safety, Validation & Rate Limit Hooks
Phase 10B: MySQL FULLTEXT search + ranking (safe fallback to icontains).
Phase 10B.1: Safety checks — min length, sanitization, logging, ranking protection.
Phase 10B.2: Optional improvements — stop-word filtering, multi-word ranking boost.
Phase 10C: Search result caching (deterministic key, 5 min TTL).
Phase 10D: Intelligent search suggestions (autocomplete).
"""

import hashlib
import logging
import re
from typing import Optional, Tuple, List, Any

from django.db import connection, transaction, IntegrityError
from django.db.models import Q, Case, When, IntegerField, Count, Value, F
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache

from profiles.models import PanditProfile
from masterdata.models import City, LocalArea, Pooja

from search.models import SearchQueryLog, RelatedSearchLog, SearchResultClick

User = get_user_model()
logger = logging.getLogger(__name__)

# Phase 10C: Cache TTL for search results (seconds)
SEARCH_CACHE_TIMEOUT = 300

# Phase 10D: Suggestions
MIN_SUGGESTION_QUERY_LENGTH = 2
MAX_SUGGESTIONS = 8
SUGGESTION_CACHE_TIMEOUT = 300
SUGGESTION_CACHE_KEY_PREFIX = "search:suggestions:"

# Phase 10E: Trending searches
TRENDING_SEARCH_CACHE_KEY = "search:trending"
TRENDING_SEARCH_CACHE_TIMEOUT = 600

# Phase 10F: Related searches
RELATED_SEARCH_CACHE_KEY_PREFIX = "search:related:"
RELATED_SEARCH_CACHE_TIMEOUT = 600
RELATED_SEARCH_MAX = 6

# Phase 10B: Max candidates from FULLTEXT before applying filters (avoids huge result sets)
FULLTEXT_CANDIDATE_LIMIT = 500
# Ranking weights: relevance (FULLTEXT), review count, profile approval
# Phase 11E: Add click weight; rebalance so relevance stays dominant
RANK_RELEVANCE_WEIGHT = 0.6
RANK_REVIEW_WEIGHT = 0.2
RANK_CLICK_WEIGHT = 0.15
RANK_APPROVAL_WEIGHT = 0.05
RANK_REVIEW_CAP = 10  # Cap review count contribution
RANK_CLICK_CAP = 20   # Phase 11E: Cap click count for normalization (min(clicks, 20)/20)
ENABLE_CLICK_RANKING = True  # Phase 11E: If False, use original formula (no click signal)

# Phase 10B.2: Multi-word ranking weights (when len(tokens) > 1)
RANK_RELEVANCE_WEIGHT_MULTI = 0.65
RANK_REVIEW_WEIGHT_MULTI = 0.2
RANK_MULTIWORD_WEIGHT = 0.15

# Phase 10B.1: Min length for FULLTEXT (MySQL ignores very short words)
MIN_QUERY_LENGTH_FULLTEXT = 3
# Phase 10B.1: Max query length to prevent abuse
MAX_QUERY_LENGTH = 100

# Phase 10B.2: Stop words (filtered before FULLTEXT; if all tokens removed, fallback to icontains)
STOP_WORDS = frozenset({
    "the", "and", "or", "in", "of", "to", "a", "for", "with",
})


def _search_filters_hash(**kwargs: Any) -> str:
    """Phase 10C: Deterministic hash of search filter params for cache key."""
    parts = []
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        if v is None:
            continue
        parts.append(f"{k}={v}")
    s = "|".join(parts)
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:16]


class SearchService:
    """
    Service for search operations.
    
    All methods are read-only.
    No mutations, no side effects, no business logic.
    """
    
    @staticmethod
    def validate_search_params(
        city_id: Optional[int] = None,
        area_id: Optional[int] = None,
        pooja_id: Optional[int] = None,
        day_of_week: Optional[int] = None,
        specific_date: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate search parameters.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate city_id
        city = None
        if city_id is not None:
            try:
                city = City.objects.get(id=city_id, is_active=True)
            except City.DoesNotExist:
                return False, f"Invalid city_id: {city_id}"
        
        # Validate area_id
        if area_id is not None:
            try:
                area = LocalArea.objects.get(id=area_id, is_active=True)
                # If city_id is also provided, validate area belongs to city
                if city_id is not None and area.city_id != city_id:
                    return False, f"Area {area_id} does not belong to city {city_id}"
            except LocalArea.DoesNotExist:
                return False, f"Invalid area_id: {area_id}"
        
        # Validate pooja_id
        if pooja_id is not None:
            try:
                Pooja.objects.get(id=pooja_id, is_active=True)
            except Pooja.DoesNotExist:
                return False, f"Invalid pooja_id: {pooja_id}"
        
        # Validate day_of_week
        if day_of_week is not None:
            if day_of_week < 0 or day_of_week > 6:
                return False, "day_of_week must be between 0 and 6 (Monday=0, Sunday=6)"
        
        # Validate specific_date format (basic check)
        if specific_date is not None:
            from django.utils.dateparse import parse_date
            parsed_date = parse_date(specific_date)
            if parsed_date is None:
                return False, "Invalid specific_date format. Use YYYY-MM-DD"
        
        return True, ""

    @staticmethod
    def is_search_cacheable(query: Optional[str]) -> bool:
        """
        Phase 10C: Only cache meaningful searches.
        Not cacheable: empty, length < MIN_QUERY_LENGTH_FULLTEXT, or > MAX_QUERY_LENGTH.
        """
        if not query:
            return False
        s = SearchService._sanitize_search_query(query)
        if not s:
            return False
        return MIN_QUERY_LENGTH_FULLTEXT <= len(s) <= MAX_QUERY_LENGTH

    @staticmethod
    def build_search_cache_key(
        query: Optional[str],
        page: int,
        page_size: int,
        city_id: Optional[int] = None,
        area_id: Optional[int] = None,
        pooja_id: Optional[int] = None,
        day_of_week: Optional[int] = None,
        specific_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        enable_call: Optional[bool] = None,
        enable_whatsapp: Optional[bool] = None,
    ) -> str:
        """Phase 10C: Deterministic cache key for search results."""
        sanitized = SearchService._sanitize_search_query(query) if query else ""
        q_part = sanitized or "_"
        f_hash = _search_filters_hash(
            city_id=city_id,
            area_id=area_id,
            pooja_id=pooja_id,
            day_of_week=day_of_week,
            specific_date=str(specific_date) if specific_date else None,
            start_time=start_time,
            end_time=end_time,
            enable_call=enable_call,
            enable_whatsapp=enable_whatsapp,
        )
        return f"search:pandits:{q_part}:{page}:{page_size}:{f_hash}"
    
    @staticmethod
    def _search_pandits_base_queryset():
        """Build base active-pandit queryset with select_related/prefetch_related (Phase 10B: avoid N+1)."""
        return User.objects.filter(
            role='pandit',
            status='active',
            is_active=True,
        ).exclude(status='deactivated').exclude(status='rejected').select_related(
            'pandit_profile'
        ).prefetch_related(
            'pandit_profile__cities_served',
            'pandit_profile__areas_served',
            'pandit_profile__poojas_performed',
        )

    @staticmethod
    def _sanitize_search_query(query: Optional[str]) -> str:
        """
        Phase 10B.1: Normalize and sanitize search query.
        Returns stripped, lowercased, whitespace-collapsed string; max 100 chars. Empty if invalid.
        """
        if query is None:
            return ''
        s = (query or '').strip()
        if not s:
            return ''
        s = s.lower()
        s = re.sub(r'\s+', ' ', s)
        if len(s) > MAX_QUERY_LENGTH:
            s = s[:MAX_QUERY_LENGTH]
        return s

    @staticmethod
    def _apply_stop_words(sanitized_query: str) -> Tuple[str, List[str]]:
        """
        Phase 10B.2: Remove stop words from sanitized query. Returns (query_after_stop_words, tokens).
        If all tokens are stop words, returns (sanitized_query, []) so caller can fallback to icontains.
        """
        if not sanitized_query:
            return '', []
        tokens = [t for t in sanitized_query.split() if t and t not in STOP_WORDS]
        if not tokens:
            return sanitized_query, []
        return ' '.join(tokens), tokens

    @staticmethod
    def _fulltext_search_pandit_candidates(query: str) -> List[Tuple[int, float]]:
        """
        Phase 10B: Run MySQL FULLTEXT on profiles_panditprofile. Returns list of (user_id, relevance).
        Only runs when connection.vendor == 'mysql'. Empty list on non-MySQL or error.
        Phase 10B.1: Uses MIN_QUERY_LENGTH_FULLTEXT; LIMIT enforced; try/except protects execution.
        """
        if connection.vendor != 'mysql':
            return []
        query = (query or '').strip()
        if not query or len(query) < MIN_QUERY_LENGTH_FULLTEXT:
            return []
        if len(query) > MAX_QUERY_LENGTH:
            query = query[:MAX_QUERY_LENGTH]
        sql = """
            SELECT p.user_id,
                   MATCH(p.display_name, p.about_description)
                       AGAINST (%s IN NATURAL LANGUAGE MODE) AS relevance
            FROM profiles_panditprofile p
            WHERE MATCH(p.display_name, p.about_description)
                      AGAINST (%s IN NATURAL LANGUAGE MODE)
              AND p.is_profile_approved = 1
            ORDER BY relevance DESC
            LIMIT %s
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, [query, query, FULLTEXT_CANDIDATE_LIMIT])
                return [(row[0], float(row[1] or 0)) for row in cursor.fetchall()]
        except Exception as e:
            logger.warning("FULLTEXT search failed, will fallback: %s", e)
            return []

    @staticmethod
    def _rank_and_order_user_ids(
        user_id_relevance: List[Tuple[int, float]],
        query_tokens: Optional[List[str]] = None,
    ):
        """
        Phase 10B: Combine FULLTEXT relevance with review count and approval.
        Phase 10B.2: When query_tokens and len > 1, add multi-word boost.
        Phase 11E: Single-token path uses click popularity when ENABLE_CLICK_RANKING:
        final_score = relevance*0.6 + review*0.2 + click*0.15 + approval*0.05.
        Returns ordered list of user ids (best first).
        """
        if not user_id_relevance:
            return []
        from reviews.models import Review

        user_ids = [u[0] for u in user_id_relevance]
        relevance_by_user = {u[0]: u[1] for u in user_id_relevance}
        max_rel = max(r for _, r in user_id_relevance) or 1.0
        review_counts = (
            Review.objects.filter(
                pandit_id__in=user_ids,
                visibility_state=Review.VISIBLE,
            )
            .values('pandit_id')
            .annotate(cnt=Count('id'))
        )
        review_by_user = {
            r['pandit_id']: min(r['cnt'] or 0, RANK_REVIEW_CAP) for r in review_counts
        }

        # Phase 11E: Click counts once per search (no query in loop)
        click_map = {}
        if ENABLE_CLICK_RANKING:
            click_map = SearchRankingSignalsService.get_click_counts(user_ids)

        # Phase 10B.2: Multi-word ranking — token_matches per user (Step 4: default 0, no div by zero)
        total_tokens = len(query_tokens) if query_tokens else 0
        use_multiword = total_tokens > 1
        token_matches_by_user = {}
        if use_multiword and total_tokens > 0:
            profiles = PanditProfile.objects.filter(
                user_id__in=user_ids
            ).values('user_id', 'display_name', 'about_description')
            for p in profiles:
                profile_text = ' '.join(
                    filter(None, [
                        (p.get('display_name') or ''),
                        (p.get('about_description') or ''),
                    ])
                ).lower()
                token_matches = sum(1 for t in query_tokens if t and t in profile_text)
                token_matches_by_user[p['user_id']] = token_matches
            logger.debug(
                "multi-word ranking applied for query='%s' (tokens=%d)",
                ' '.join(query_tokens),
                total_tokens,
            )

        scores = []
        for uid in user_ids:
            rel = relevance_by_user.get(uid, 0) / max_rel
            review_count = review_by_user.get(uid, 0) or 0
            review_score = review_count / float(RANK_REVIEW_CAP)
            if use_multiword and total_tokens > 0:
                token_matches = token_matches_by_user.get(uid, 0)
                multiword_bonus = token_matches / total_tokens
                score = (
                    RANK_RELEVANCE_WEIGHT_MULTI * rel
                    + RANK_REVIEW_WEIGHT_MULTI * review_score
                    + RANK_MULTIWORD_WEIGHT * multiword_bonus
                )
            else:
                # Phase 11E: Smart ranking with click popularity (or original formula if disabled)
                clicks = click_map.get(uid, 0) if ENABLE_CLICK_RANKING else 0
                click_score = min(clicks, RANK_CLICK_CAP) / float(RANK_CLICK_CAP) if ENABLE_CLICK_RANKING else 0.0
                if ENABLE_CLICK_RANKING:
                    score = (
                        RANK_RELEVANCE_WEIGHT * rel
                        + RANK_REVIEW_WEIGHT * review_score
                        + RANK_CLICK_WEIGHT * click_score
                        + RANK_APPROVAL_WEIGHT * 1.0
                    )
                    logger.debug(
                        "ranking signals applied: relevance=%s review=%s clicks=%s",
                        rel,
                        review_score,
                        click_score,
                    )
                else:
                    score = (
                        0.7 * rel
                        + 0.2 * review_score
                        + 0.1 * 1.0
                    )
            scores.append((uid, score))
        scores.sort(key=lambda x: -x[1])
        return [x[0] for x in scores]

    @staticmethod
    def search_pandits(
        city_id: Optional[int] = None,
        area_id: Optional[int] = None,
        pooja_id: Optional[int] = None,
        day_of_week: Optional[int] = None,
        specific_date: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        exclude_fully_blocked: bool = True,
        enable_call: Optional[bool] = None,
        enable_whatsapp: Optional[bool] = None,
        query: Optional[str] = None,
    ):
        """
        Search for Pandits based on criteria.

        Phase 10B: When `query` is provided and DB is MySQL, uses FULLTEXT ranking;
        otherwise (or if FULLTEXT returns no results) falls back to icontains.
        Pagination and response shape unchanged.

        Returns:
            QuerySet of User objects with role='pandit' and status='active'
        """
        # Base queryset with efficient loading (Step 6)
        queryset = SearchService._search_pandits_base_queryset()

        # Phase 10B.1: Sanitize query (strip, lower, collapse whitespace, truncate to 100)
        sanitized = SearchService._sanitize_search_query(query)
        if not sanitized:
            search_query = None
            query_tokens = []
        else:
            # Phase 10B.2: Stop-word filtering; if all tokens removed, fallback to icontains with original
            query_after_stop, query_tokens = SearchService._apply_stop_words(sanitized)
            search_query = query_after_stop if query_tokens else sanitized

        used_fulltext_order = False
        if search_query:
            # FULLTEXT only when MySQL, length >= 3, and at least one non–stop-word token
            use_fulltext = (
                connection.vendor == 'mysql'
                and len(search_query) >= MIN_QUERY_LENGTH_FULLTEXT
                and len(query_tokens) > 0
            )
            if use_fulltext:
                candidates = SearchService._fulltext_search_pandit_candidates(search_query)
                if candidates:
                    logger.info(
                        "FULLTEXT search executed for query='%s' (candidates=%d)",
                        search_query[:50], len(candidates),
                    )
                    ordered_ids = SearchService._rank_and_order_user_ids(
                        candidates,
                        query_tokens=query_tokens if len(query_tokens) > 1 else None,
                    )
                    queryset = queryset.filter(id__in=ordered_ids)
                    order = Case(
                        *[When(id=uid, then=Value(pos)) for pos, uid in enumerate(ordered_ids)],
                        output_field=IntegerField(),
                    )
                    queryset = queryset.order_by(order)
                    used_fulltext_order = True
                else:
                    logger.info(
                        "Fallback search (icontains) for query='%s' (FULLTEXT returned no results)",
                        search_query[:50],
                    )
                    queryset = queryset.filter(
                        Q(pandit_profile__display_name__icontains=search_query)
                        | Q(pandit_profile__about_description__icontains=search_query)
                    ).distinct()
            else:
                if connection.vendor == 'mysql' and search_query:
                    logger.info(
                        "Fallback search (icontains) for query='%s' (query length < %d)",
                        search_query[:50], MIN_QUERY_LENGTH_FULLTEXT,
                    )
                elif connection.vendor != 'mysql' and search_query:
                    logger.debug(
                        "icontains search for query='%s' (non-MySQL)",
                        search_query[:50],
                    )
                queryset = queryset.filter(
                    Q(pandit_profile__display_name__icontains=search_query)
                    | Q(pandit_profile__about_description__icontains=search_query)
                ).distinct()

        # Filter by city
        if city_id:
            queryset = queryset.filter(
                pandit_profile__cities_served__id=city_id
            ).distinct()

        # Filter by area
        if area_id:
            queryset = queryset.filter(
                pandit_profile__areas_served__id=area_id
            ).distinct()

        # Filter by pooja
        if pooja_id:
            queryset = queryset.filter(
                pandit_profile__poojas_performed__id=pooja_id
            ).distinct()

        # Filter by availability (day_of_week)
        if day_of_week is not None:
            from availability.models import Availability
            queryset = queryset.filter(
                pandit_profile__availability__day_of_week=day_of_week,
                pandit_profile__availability__is_available=True
            ).distinct()

        # Filter by availability (specific_date)
        if specific_date:
            from django.utils.dateparse import parse_date
            parsed_date = parse_date(specific_date)
            if parsed_date:
                day_of_week_for_date = parsed_date.weekday()
                from availability.models import Availability
                queryset = queryset.filter(
                    pandit_profile__availability__day_of_week=day_of_week_for_date,
                    pandit_profile__availability__is_available=True
                ).distinct()

        # Filter by time range
        if start_time or end_time:
            from django.utils.dateparse import parse_time
            availability_filter = Q()
            if start_time:
                parsed_start = parse_time(start_time)
                if parsed_start:
                    availability_filter |= Q(
                        pandit_profile__availability__start_time__lte=parsed_start
                    )
            if end_time:
                parsed_end = parse_time(end_time)
                if parsed_end:
                    availability_filter |= Q(
                        pandit_profile__availability__end_time__gte=parsed_end
                    )
            if availability_filter:
                queryset = queryset.filter(availability_filter).distinct()

        # Filter by call availability
        if enable_call is not None:
            if enable_call:
                queryset = queryset.filter(
                    Q(pandit_profile__enable_call=True) | Q(pandit_profile__allow_call=True)
                ).distinct()
            else:
                queryset = queryset.filter(
                    pandit_profile__enable_call=False,
                    pandit_profile__allow_call=False
                ).distinct()

        # Filter by WhatsApp availability
        if enable_whatsapp is not None:
            if enable_whatsapp:
                queryset = queryset.filter(
                    Q(pandit_profile__enable_whatsapp=True) | Q(pandit_profile__allow_whatsapp=True)
                ).distinct()
            else:
                queryset = queryset.filter(
                    pandit_profile__enable_whatsapp=False,
                    pandit_profile__allow_whatsapp=False
                ).distinct()

        if exclude_fully_blocked:
            pass

        # Step 5: Default order (newest first) unless FULLTEXT ranking was applied
        if not used_fulltext_order:
            queryset = queryset.order_by('-created_at')

        return queryset

    @staticmethod
    def get_search_suggestions(query: Optional[str]) -> List[str]:
        """
        Phase 10D: Return top search suggestion strings for autocomplete.
        Uses PanditProfile (display_name, about_description) and Page (title, description).
        Cached per query; rejects query len < 2 or > MAX_QUERY_LENGTH.
        """
        # Step 2: Sanitize and reject too short / too long (Steps 2, 10)
        q = SearchService._sanitize_search_query(query)
        if not q or len(q) < MIN_SUGGESTION_QUERY_LENGTH:
            return []
        if len(q) > MAX_QUERY_LENGTH:
            return []

        cache_key = f"{SUGGESTION_CACHE_KEY_PREFIX}{q}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Step 3: PanditProfile — display_name, about_description, limit 10
        profile_qs = PanditProfile.objects.filter(
            is_profile_approved=True
        ).filter(
            Q(display_name__icontains=q) | Q(about_description__icontains=q)
        ).values_list("display_name", "about_description")[:10]

        # Step 4: Page (temple) — title, description, limit 10
        from pages.models import Page
        from pages.constants import PAGE_STATUS_ACTIVE
        page_qs = Page.objects.filter(
            status=PAGE_STATUS_ACTIVE,
            is_deleted=False,
        ).filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).values_list("title", "description")[:10]

        # Step 5: Extract tokens (words), filter stop words and short
        token_frequency = {}
        phrases_seen = set()

        for name, desc in profile_qs:
            for raw in (name, desc):
                if not raw:
                    continue
                text = (raw or "").lower()
                phrases_seen.add((text.strip()[:80] if text.strip() else ""))
                for word in re.findall(r"[a-z0-9]+", text):
                    if len(word) < MIN_SUGGESTION_QUERY_LENGTH or word in STOP_WORDS:
                        continue
                    token_frequency[word] = token_frequency.get(word, 0) + 1

        for title, desc in page_qs:
            for raw in (title, desc):
                if not raw:
                    continue
                text = (raw or "").lower()
                phrases_seen.add((text.strip()[:80] if text.strip() else ""))
                for word in re.findall(r"[a-z0-9]+", text):
                    if len(word) < MIN_SUGGESTION_QUERY_LENGTH or word in STOP_WORDS:
                        continue
                    token_frequency[word] = token_frequency.get(word, 0) + 1

        # Step 6: Rank by frequency; include tokens that contain query; add short phrases
        suggestions = []
        # Tokens containing (or starting with) query, sorted by frequency desc
        for token, count in sorted(
            token_frequency.items(),
            key=lambda x: (-x[1], x[0]),
        ):
            if q in token or token.startswith(q):
                suggestions.append(token)
            if len(suggestions) >= MAX_SUGGESTIONS:
                break
        # Add phrases that contain query (display_name / title), prefer short
        for phrase in sorted(phrases_seen, key=lambda x: len(x)):
            if not phrase or q not in phrase or phrase in suggestions:
                continue
            if len(phrase) > 50:
                phrase = phrase[:47] + "..."
            suggestions.append(phrase)
            if len(suggestions) >= MAX_SUGGESTIONS:
                break
        # Dedupe preserving order, then cap
        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        suggestions = unique[:MAX_SUGGESTIONS]
        if not suggestions and q in token_frequency:
            suggestions = [q]
        elif not suggestions:
            suggestions = list(
                sorted(token_frequency.keys(), key=lambda t: -token_frequency[t])
            )[:MAX_SUGGESTIONS]

        # Phase 10E: Slight priority for suggestions that appear in trending
        try:
            trending = SearchAnalyticsService.get_trending_searches()
            trending_lower = {t.lower() for t in trending}
            in_trending = [s for s in suggestions if s.lower() in trending_lower]
            not_in_trending = [s for s in suggestions if s.lower() not in trending_lower]
            suggestions = (in_trending + not_in_trending)[:MAX_SUGGESTIONS]
        except Exception:
            pass

        cache.set(cache_key, suggestions, timeout=SUGGESTION_CACHE_TIMEOUT)
        logger.debug("search suggestions generated for query='%s'", q)
        return suggestions

    @staticmethod
    def debug_fulltext_explain(query: str):
        """
        Phase 10B.1: Debug helper only. Runs EXPLAIN on the FULLTEXT pandit search query.
        Use from Django shell to verify index usage (e.g. key=pandit_search_idx, type=fulltext).
        Does not run automatically.
        """
        if connection.vendor != 'mysql':
            return []
        q = (query or '').strip()[:MAX_QUERY_LENGTH]
        if not q:
            return []
        sql = """
            EXPLAIN SELECT p.user_id,
                   MATCH(p.display_name, p.about_description)
                       AGAINST (%s IN NATURAL LANGUAGE MODE) AS relevance
            FROM profiles_panditprofile p
            WHERE MATCH(p.display_name, p.about_description)
                      AGAINST (%s IN NATURAL LANGUAGE MODE)
              AND p.is_profile_approved = 1
            ORDER BY relevance DESC
            LIMIT %s
        """
        with connection.cursor() as cursor:
            cursor.execute(sql, [q, q, FULLTEXT_CANDIDATE_LIMIT])
            rows = cursor.fetchall()
        return list(rows)


class SearchAnalyticsService:
    """
    Phase 10E: Lightweight search analytics for trending searches.
    Tracks query counts; does not store PII. Cached trending list.
    """

    @staticmethod
    def track_search_query(query: Optional[str]) -> None:
        """
        Log a search query for analytics. Sanitizes and normalizes; ignores short/long/numbers-only.
        Concurrency-safe: unique normalized_query + atomic get_or_create + F() update + IntegrityError fallback.
        """
        sanitized = SearchService._sanitize_search_query(query)
        if not sanitized:
            return
        if len(sanitized) < MIN_QUERY_LENGTH_FULLTEXT:
            return
        if len(sanitized) > MAX_QUERY_LENGTH:
            return
        if sanitized.isdigit() or sanitized.replace(" ", "").isdigit():
            return
        normalized = sanitized.lower().strip()
        display = (query or "").strip()[:100] or normalized
        try:
            with transaction.atomic():
                obj, created = SearchQueryLog.objects.get_or_create(
                    normalized_query=normalized,
                    defaults={
                        "query": display,
                        "search_count": 1,
                    },
                )
                if not created:
                    SearchQueryLog.objects.filter(pk=obj.pk).update(
                        search_count=F("search_count") + 1,
                        last_searched_at=timezone.now(),
                        query=display,
                    )
        except IntegrityError:
            # Another thread created the row simultaneously
            SearchQueryLog.objects.filter(normalized_query=normalized).update(
                search_count=F("search_count") + 1,
                last_searched_at=timezone.now(),
                query=display,
            )
        logger.debug("search query tracked: %s", normalized)

    @staticmethod
    def get_trending_searches() -> List[str]:
        """
        Return top 10 trending search strings. Cached 10 minutes.
        """
        cached = cache.get(TRENDING_SEARCH_CACHE_KEY)
        if cached is not None:
            logger.debug("trending searches cache hit")
            return cached
        logger.debug("trending searches cache miss")
        qs = (
            SearchQueryLog.objects.order_by("-search_count")
            .values_list("query", flat=True)[:10]
        )
        result = list(qs)
        cache.set(TRENDING_SEARCH_CACHE_KEY, result, timeout=TRENDING_SEARCH_CACHE_TIMEOUT)
        return result

    @staticmethod
    def track_related_search(previous_query: Optional[str], current_query: Optional[str]) -> None:
        """
        Phase 10F: Log a search sequence (previous → current) for related-searches.
        Sanitizes both; ignores if same, length < 3, length > 100, or numeric-only.
        """
        if not previous_query or not current_query:
            return
        prev = SearchService._sanitize_search_query(previous_query)
        curr = SearchService._sanitize_search_query(current_query)
        if not prev or not curr or prev == curr:
            return
        if len(prev) < MIN_QUERY_LENGTH_FULLTEXT or len(curr) < MIN_QUERY_LENGTH_FULLTEXT:
            return
        if len(prev) > MAX_QUERY_LENGTH or len(curr) > MAX_QUERY_LENGTH:
            return
        if prev.isdigit() or prev.replace(" ", "").isdigit():
            return
        if curr.isdigit() or curr.replace(" ", "").isdigit():
            return
        prev_norm = prev.lower().strip()
        curr_norm = curr.lower().strip()
        if prev_norm == curr_norm:
            return
        obj, created = RelatedSearchLog.objects.get_or_create(
            source_query=prev_norm,
            related_query=curr_norm,
            defaults={"pair_count": 1},
        )
        if not created:
            obj.pair_count += 1
            obj.save(update_fields=["pair_count", "last_seen"])
        logger.debug("related search tracked: %s -> %s", prev_norm, curr_norm)

    @staticmethod
    def get_related_searches(query: Optional[str]) -> List[str]:
        """
        Phase 10F: Return related search strings for the given query. Cached 10 minutes.
        """
        if not query:
            return []
        q = SearchService._sanitize_search_query(query)
        if not q or len(q) < MIN_QUERY_LENGTH_FULLTEXT:
            return []
        key_norm = q.lower().strip()[:MAX_QUERY_LENGTH]
        cache_key = f"{RELATED_SEARCH_CACHE_KEY_PREFIX}{key_norm}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("related search cache hit")
            return cached
        logger.debug("related search cache miss")
        qs = (
            RelatedSearchLog.objects.filter(source_query=key_norm)
            .order_by("-pair_count")
            .values_list("related_query", flat=True)[:RELATED_SEARCH_MAX]
        )
        result = list(qs)
        cache.set(cache_key, result, timeout=RELATED_SEARCH_CACHE_TIMEOUT)
        return result


class SearchClickTrackingService:
    """
    Phase 11C1: Tracks which pandit profiles users click from search results.
    Abuse protection: query length >= 3, valid pandit, no duplicate from same session within 5s.
    """
    MIN_QUERY_LENGTH_TRACK = 3
    DUPLICATE_CLICK_WINDOW_SECONDS = 5

    @staticmethod
    def track_click(
        query: Optional[str],
        pandit_profile: Optional[PanditProfile],
        user=None,
        session_id: Optional[str] = None,
    ) -> None:
        if not pandit_profile:
            return
        sanitized_query = SearchService._sanitize_search_query(query or "")
        if not sanitized_query or len(sanitized_query) < SearchClickTrackingService.MIN_QUERY_LENGTH_TRACK:
            return
        sid = (session_id or "").strip()
        if sid:
            from django.utils import timezone
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(seconds=SearchClickTrackingService.DUPLICATE_CLICK_WINDOW_SECONDS)
            if SearchResultClick.objects.filter(
                session_id=sid,
                pandit=pandit_profile,
                clicked_at__gte=cutoff,
            ).exists():
                return
        SearchResultClick.objects.create(
            query=sanitized_query[:100],
            pandit=pandit_profile,
            user=user if (user and getattr(user, "is_authenticated", False)) else None,
            session_id=sid or "",
        )
        logger.debug(
            "search click tracked query=%s pandit=%s",
            sanitized_query[:50],
            pandit_profile.id,
        )


class SearchRankingSignalsService:
    """
    Phase 11E: Provides behavioral signals for search ranking (e.g. click popularity).
    One query per search; no queries inside ranking loop.
    """
    @staticmethod
    def get_click_counts(user_ids):
        if not user_ids:
            return {}
        rows = (
            SearchResultClick.objects.filter(pandit__user_id__in=user_ids)
            .values("pandit__user_id")
            .annotate(cnt=Count("id"))
        )
        return {r["pandit__user_id"]: (r["cnt"] or 0) for r in rows}


class PageSearchService:
    """
    Service for Page/Temple search operations.
    
    All methods are read-only.
    No mutations, no side effects, no business logic.
    Isolated from Pandit search.
    """
    
    @staticmethod
    def search_pages(
        city_id: Optional[int] = None,
        area_id: Optional[int] = None,
        page_type: Optional[str] = None,
        keyword: Optional[str] = None,
        has_announcements: Optional[bool] = None,
        has_events: Optional[bool] = None,
        recently_updated: Optional[bool] = None
    ):
        """
        Search for Pages based on criteria.
        
        Args:
            city_id: Filter by city
            area_id: Filter by area
            page_type: Filter by page type (TEMPLE, BRAND, etc.)
            keyword: Search in title and description
            has_announcements: Filter pages with announcements
            has_events: Filter pages with upcoming events
            recently_updated: Filter recently updated pages
        
        Returns:
            QuerySet of Page objects with status=ACTIVE and is_deleted=False
        
        Note:
            - Only returns ACTIVE pages
            - INVISIBLE pages are excluded from search (but accessible via direct URL)
            - Read-only query, no mutations
        """
        from pages.models import Page
        from pages.constants import PAGE_STATUS_ACTIVE, PAGE_STATUS_INVISIBLE, PAGE_STATUS_DEACTIVATED
        
        # TASK 19: Base queryset: Active pages only, not deleted (visibility enforced at query time)
        # Database is authoritative - never show invisible/deactivated pages
        # Index is derived, not truth - filtering always applied before returning results
        queryset = Page.objects.filter(
            status=PAGE_STATUS_ACTIVE,  # TASK 19: Only ACTIVE status
            is_deleted=False,            # TASK 19: Never show deleted pages
            # TASK 19: Exclude INVISIBLE pages from search (but accessible via direct URL)
        ).exclude(
            status=PAGE_STATUS_INVISIBLE  # TASK 19: Exclude invisible pages from search
        ).exclude(
            status=PAGE_STATUS_DEACTIVATED  # TASK 19: Exclude deactivated pages from search
        ).select_related('city', 'area', 'created_by')
        
        # Filter by page_type
        if page_type:
            queryset = queryset.filter(page_type=page_type)
        
        # Filter by city
        if city_id:
            queryset = queryset.filter(city_id=city_id)
        
        # Filter by area
        if area_id:
            queryset = queryset.filter(area_id=area_id)
        
        # Filter by keyword (search in title and description)
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(address__icontains=keyword)
            )
        
        # Filter by has_announcements (pages with posts of type ANNOUNCEMENT)
        if has_announcements:
            from pages.models import PagePost
            pages_with_announcements = PagePost.objects.filter(
                post_type='ANNOUNCEMENT',
                is_deleted=False,
                is_hidden=False
            ).values_list('page_id', flat=True).distinct()
            queryset = queryset.filter(id__in=pages_with_announcements)
        
        # Filter by has_events (pages with posts of type EVENT)
        if has_events:
            from pages.models import PagePost
            from django.utils import timezone
            pages_with_events = PagePost.objects.filter(
                post_type='EVENT',
                is_deleted=False,
                is_hidden=False,
                event_date__gte=timezone.now().date()
            ).values_list('page_id', flat=True).distinct()
            queryset = queryset.filter(id__in=pages_with_events)
        
        # Filter by recently_updated (updated in last 30 days)
        if recently_updated:
            from django.utils import timezone
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(updated_at__gte=thirty_days_ago)
        
        # Order by creation date (newest first)
        queryset = queryset.order_by('-created_at')
        
        return queryset


class RecommendationService:
    """
    Phase 11F: Recommendation engine for Pandits.
    Uses click popularity, review counts, and existing analytics (read-only).
    """

    @staticmethod
    def get_popular_pandits(limit=10):
        """Return most-clicked pandits from search result clicks (approved profiles only)."""
        from search.models import SearchResultClick
        from profiles.models import PanditProfile
        from django.db.models import Count

        rows = (
            SearchResultClick.objects.values("pandit")
            .annotate(clicks=Count("id"))
            .order_by("-clicks")[:limit]
        )
        pandit_ids = [r["pandit"] for r in rows]
        profiles = (
            PanditProfile.objects.filter(
                id__in=pandit_ids, is_profile_approved=True
            ).select_related("user")
        )
        return list(profiles)

    @staticmethod
    def get_top_reviewed_pandits(limit=10):
        """Return pandits with most reviews (Review.pandit is User; resolve to PanditProfile)."""
        from reviews.models import Review
        from profiles.models import PanditProfile
        from django.db.models import Count

        rows = (
            Review.objects.values("pandit")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:limit]
        )
        user_ids = [r["pandit"] for r in rows]
        profiles = PanditProfile.objects.filter(
            user_id__in=user_ids,
            is_profile_approved=True,
        ).select_related("user")
        return list(profiles)

    @staticmethod
    def get_recommended_pandits(limit=10):
        """Hybrid: combine popular (clicks) and top-reviewed, deduplicate by profile id, return up to limit."""
        popular = RecommendationService.get_popular_pandits(limit=limit)
        reviewed = RecommendationService.get_top_reviewed_pandits(limit=limit)
        combined = list(popular) + list(reviewed)
        unique = {}
        for p in combined:
            unique[p.id] = p
        return list(unique.values())[:limit]
