# Nitya Dharma — System Architecture & Data Audit

**Document type:** Read-only audit (no code or schema changes performed for this document).  
**Scope:** Django project under repository root containing `manage.py` (`Nitya_Dharma_project`).  
**Generated:** 2026-04-04 (from static source inspection).  
**Uncertainty rule:** Where behavior could not be verified without runtime inspection, entries are marked **NEEDS VERIFICATION**.

---

## Section 1: Project Overview

### System type

**Nitya Dharma** is a **web platform for discovering Pandits and temple/community pages**, combining:

- **Marketplace-style discovery** (search, profiles, trust signals, recommendations).
- **Non-transactional booking signals** via **Booking Intent** (explicitly not a reservation/payment system in model documentation).
- **Content pages** (temple/brand/trust/social service **Pages** with posts, gallery, reviews).
- **Governance and moderation** patterns (reviews, partial blocks, referrals, kill switch, feature flags).

### Major Django apps (from `INSTALLED_APPS`)

| Area | Apps |
|------|------|
| Core / infra | `core`, `security`, `maintenance`, `monitoring` |
| Identity & access | `accounts` |
| Profiles | `profiles` |
| Pages / CMS | `pages` |
| Discovery | `search`, `recommendations`, `recommendation_engine`, `feed_engine` |
| Intent & availability | `booking_intent`, `availability` |
| Social proof | `reviews`, `trust_display` |
| Engagement | `engagement`, `behavior_engine`, `notifications` |
| Referrals & master data | `referrals`, `masterdata` |
| Ops / admin UI | `dashboards`, `branding`, `tracking_config`, `ads`, `ads_analytics` |
| Analytics | `analytics`, `analytics_dashboard`, `admin_intelligence` (mounted via dashboards) |
| Governance | `governance` (+ subpackages) |
| Support | `support` |

**NEEDS VERIFICATION:** Exact production deployment topology (single VPS vs split services) and which optional apps are enabled in a given environment.

### Roles in the system

| Role label (product) | Implementation (code-level) |
|----------------------|------------------------------|
| **Super Admin** | Django `User.is_superuser == True`. Full access to `/dashboard/super-admin/` and related units. |
| **Admin / Admin Pandit** | `User.role == 'admin'` and typically **not** superuser; routed to `/dashboard/admin-pandit/`. Approves pandits/profiles per views. |
| **Pandit** | `User.role == 'pandit'`; profile, booking intents received, referrals, etc. |
| **End User** | `User.role == 'user'`; search, booking intent as requester, reviews, follows, notifications. |

Additional **account statuses** (`pending`, `active`, `rejected`, `deactivated`) gate what a user can do regardless of role.

### High-level architecture

```
Browser (HTML templates + static JS/CSS)
    → Gunicorn (WSGI) / Django
        → Views (function- and class-based)
        → Services / helpers (app-specific modules)
        → Django ORM
        → MySQL (engine configured in env-specific settings: `dev.py` / `prod.py`; not defined in `settings/base.py`)
```

Supporting:

- **Static files:** `STATIC_URL=/static/`, collected to `STATIC_ROOT`, served via **WhiteNoise** (`CompressedManifestStaticFilesStorage`).
- **Media:** `MEDIA_URL=/media/`, `MEDIA_ROOT=BASE_DIR / 'media'`; served in dev / when `SERVE_MEDIA_IN_PROD` via `django.conf.urls.static.static()`.
- **Middleware:** Security, GZip, WhiteNoise, sessions, CSRF, auth, custom session validation, behavior page-view tracking, request timing, clickjacking protection.

---

## Section 2: Role-Based Data Flow

### ROLE: SUPER ADMIN (`is_superuser`)

| Direction | Data / actions (representative) |
|-----------|----------------------------------|
| **Creates** | Referral links, advertisements, CMS/static content, FAQ entries, tracking config, branding assets, master data (via tools), governance actions **NEEDS VERIFICATION** per view. |
| **Reads** | Global aggregates on super-admin dashboard (`User`, `Page`, pandit lists, SEO/crawl tools, config audit, exports, consistency checks). |
| **Updates** | Platform kill switch, feature flags, SEO overrides, page disable/restore, pandit suspend/reinstate, analytics/GTM snippets, system operational settings. |
| **Deletes** | Soft/hard patterns vary by model (e.g. pages are “no hard delete” by design); advertisement delete **NEEDS VERIFICATION** for actual DB delete vs deactivate. |

**Permissions:** Enforced by `is_superuser` checks in `dashboards/views.py` and related super-admin views.

---

### ROLE: ADMIN PANDIT (`role='admin'`, not superuser)

| Direction | Data / actions |
|-----------|----------------|
| **Creates** | Referral links (via `referrals` app **NEEDS VERIFICATION**), partial blocks, profile send-back actions. |
| **Reads** | Admin dashboard metrics (pending pandits, profiles, locations), moderation queues. |
| **Updates** | Approve/reject pandits (UI paths), approve/send-back profiles, apply/remove partial blocks. |
| **Deletes** | **NEEDS VERIFICATION** per endpoint (often status changes rather than physical delete). |

---

### ROLE: PANDIT (`role='pandit'`)

| Direction | Data / actions |
|-----------|----------------|
| **Creates** | `PanditProfile` (via onboarding **NEEDS VERIFICATION**), `BookingIntent` (as recipient), gallery images on pages they manage **NEEDS VERIFICATION**, posts **NEEDS VERIFICATION**, reviews as subject only (others write reviews). |
| **Reads** | Own profile (private), received booking intents, notifications, ad dashboards scoped to pandit **NEEDS VERIFICATION**. |
| **Updates** | Profile edit, location update API, intent viewed/cancelled flows **NEEDS VERIFICATION**, availability **NEEDS VERIFICATION**. |
| **Deletes** | **NEEDS VERIFICATION** (many domains use soft-hide or PROTECT FKs). |

---

### ROLE: END USER (`role='user'`)

| Direction | Data / actions |
|-----------|----------------|
| **Creates** | Registration (`User`), `BookingIntent` as requester, `Review` (pandit reviews), `PageReview` on temple pages, contact requests, follows, search logs **NEEDS VERIFICATION**. |
| **Reads** | Public profiles, search results, public pages, own notifications, own booking history UI. |
| **Updates** | Account settings, theme preference (AJAX), mark notifications read. |
| **Deletes** | Account delete flow **NEEDS VERIFICATION** (may be soft deactivate). |

---

## Section 3: Data Types (Models)

Below: **inventory of `models.Model` subclasses** and **representative field typing** for primary entities. For full column lists, see `models.py` in each app.

### accounts

| Model | Notes |
|-------|--------|
| `User` | Extends `AbstractUser`; `EmailField`, `CharField` roles/status, `BooleanField` flags, `ImageField` profile picture, `ForeignKey` self (`referred_by`), timestamps. |
| `EmailVerificationToken` | Token storage for email verification. |

**Table:** `accounts_user` (Django default for `accounts.User`), **`NEEDS VERIFICATION** for `EmailVerificationToken` table name (`accounts_emailverificationtoken` typical).

### pages

| Model | db_table (from model `Meta`) |
|-------|------------------------------|
| `Page` | `pages_page` |
| `PageGalleryImage` | `pages_page_gallery_image` |
| `PagePost` | `pages_page_post` |
| `PageAuditLog` | `pages_page_audit_log` |
| `PageReview` | `pages_page_review` |
| `PageRole` | `pages_page_role` |
| `PageFollow` | `pages_pagefollow` |
| `PageAccessRequest` | **NEEDS VERIFICATION** (`pages/models_access_request.py`; check `Meta`). |

**Representative `Page` fields:** `BigAutoField` PK, `CharField` `public_id`, `TextField`/`SlugField` text, `ImageField` cover/profile, `ForeignKey` to `User`, `masterdata.City`, `masterdata.LocalArea`, status/SEO JSON **NEEDS VERIFICATION** for optional SEO fields in remainder of file.

### profiles

| Model | db_table |
|-------|----------|
| `PanditProfile` | `profiles_panditprofile` |
| `PendingLocation` | `profiles_pending_location` |

Heavy use of `ForeignKey` to `User`, `CharField`, `TextField`, `ImageField`, masterdata FKs **NEEDS VERIFICATION** for full list.

### booking_intent

| Model | db_table |
|-------|----------|
| `BookingIntent` | `booking_intent_bookingintent` |

**Fields:** `ForeignKey` requester & pandit → `User`, `CharField` status/public_id, optional date/time, `TextField` message, audit timestamps.

### reviews

| Model | db_table |
|-------|----------|
| `Review` | `reviews_review` |

**Fields:** `ForeignKey` user (author), pandit (subject), `IntegerField` rating, `TextField` content, visibility `CharField`, `CharField` `public_id`.

### search

| Model | db_table |
|-------|----------|
| `SavedSearch` | `search_savedsearch` |
| `SearchQueryLog` | `search_searchquerylog` |
| `RelatedSearchLog` | `search_relatedsearchlog` |
| `SearchResultClick` | `search_result_click` |

### referrals

| Model | db_table |
|-------|----------|
| `ReferralLink` | `referrals_referral_link` |
| `ReferralUsage` | `referrals_referral_usage` |
| `ReferralPolicy` | `referrals_referral_policy` |

### notifications

| Model | Default table names expected |
|-------|------------------------------|
| `Notification` | `notifications_notification` |
| `NotificationPreference` | `notifications_notificationpreference` |

### analytics

| Model | db_table |
|-------|----------|
| `AnalyticsEvent` | `analytics_analyticsevent` |
| `AnalyticsAccessLog` | **NEEDS VERIFICATION** (see `analytics/models.py` `Meta`). |

### ads / ads_analytics

| Model | Purpose |
|-------|---------|
| `Advertisement` | Ad definitions |
| `AdImpression`, `AdClick`, `AdConversionIntent`, `AdDailyStats`, `AdPlacementStats`, `AdLocationStats`, `AdRevenueEvent` | Event + aggregate analytics |

### behavior_engine

Many models (event logs, daily aggregates, interest profiles). See `behavior_engine/models.py` and explicit `db_table` values (e.g. `behavior_event_log`, `behavior_user_behavior_event`, …).

### masterdata

Cities, mandals, local areas, pooja categories, poojas, languages, country codes, profile completion rules, upload config — all with explicit `db_table` in `Meta`.

### governance

| Model | Location |
|-------|----------|
| `GovernanceCase`, `GovernanceAction`, `PartialBlock` | `governance/models.py` |
| `ApprovalRecord`, `ApprovalCustodian` | `governance/approvals/models.py` |

`governance/appeals/models.py` and `governance/audit/models.py` appear **empty placeholders** at audit time.

### core

`FeatureToggle`, `FeatureFlag`, `PlatformKillSwitch` (+ abstract bases). Explicit `db_table` for toggles/flags/kill switch in `core/models.py`.

### engagement / feed_engine / branding / tracking_config / support

- `engagement`: interaction events, comments, likes.
- `feed_engine`: `FeedItemCandidate` (`feed_feeditemcandidate`).
- `branding`: `BrandingLogo`.
- `tracking_config`: `TrackingConfiguration`, `TrackingConfigurationAudit`.
- `support`: `ContactRequest` (indexes on status/role; **no custom `db_table`** → `support_contactrequest` typical).

### availability

`Availability` model — **NEEDS VERIFICATION** for `db_table` and usage in views.

### recommendations / security / maintenance

- `recommendations/models.py`: **no Model classes found** in grep.
- `security/models.py`, `maintenance/models.py`: **no Model classes found** in grep.

---

## Section 4: Layered Architecture Flow

### Request lifecycle (typical page)

1. **HTTP request** hits Gunicorn → Django URL resolver (`nityadharma/urls.py` + included `urls.py`).
2. **Middleware** processes request (security, session, CSRF, custom validation, optional behavior tracking).
3. **View** runs: loads `request.user`, authorizes, queries ORM, may call **service modules** (spread across apps; **NEEDS VERIFICATION** for a single unified “services” package).
4. **Template** rendered via `render()` or class-based generic views with **context** from view + **context processors** (`navbar_context`, `pooja_data`, `tracking_context`, `social_links`, `active_ads`).
5. **Response** HTML with references to `{% static %}` and `MEDIA_URL` for uploads.

### Static files

- Source: `STATICFILES_DIRS` → `BASE_DIR / 'static'`.
- Production collect: `collectstatic` → `STATIC_ROOT` / volume in Docker.
- Delivery: **WhiteNoise** middleware + compressed manifest storage.

### Media

- Uploads: Django `FileSystemStorage` to `MEDIA_ROOT`.
- URLs: `file_field.url` → `/media/...` when correctly served.
- **Production:** `urlpatterns += static(...)` only if `DEBUG` or `SERVE_MEDIA_IN_PROD`; otherwise nginx/CDN must map `/media/`.

---

## Section 5: API & Route Analysis

**Convention:** Unless noted, methods are **NEEDS VERIFICATION** (inspect view decorators). Many JSON endpoints use POST + CSRF for same-origin fetches.

### Root & core (`/`)

| URL pattern | View (symbol) | Purpose |
|-------------|---------------|---------|
| `/` | `core.views.home` | Home page |
| `/offline/` | `core.views.offline` | PWA offline |
| `/health/` | `core.health_checks.health_check` | Health |
| `/follow/pandit/<public_id>/` | `views_follow.follow_pandit` | Follow pandit |
| `/unfollow/pandit/<public_id>/` | `views_follow.unfollow_pandit` | Unfollow |
| `/follow/temple/<page_public_id>/` | `views_follow.follow_temple` | Follow page |
| `/unfollow/temple/<page_public_id>/` | `views_follow.unfollow_temple` | Unfollow page |
| `/follow/status/<entity_type>/<public_id>/` | `views_follow.check_follow_status` | Follow status JSON **NEEDS VERIFICATION** |

### Accounts (`/accounts/`)

| Path | Name | Purpose |
|------|------|---------|
| `login/` | `login` | Login |
| `register/` | `register` | End-user registration |
| `logout/` | `logout` | Logout |
| `password-reset/` … | password reset chain | Reset flow |
| `pandit/register/<token>/` | `pandit_register` | Referral pandit signup |
| `pandit/<id>/approve/`, `reject/` | approval | Admin workflow |
| `settings/` … | account settings | Profile/security/notifications |
| `verify-email/<token>/` | `verify_email` | Email verify |
| `pandits/<public_id>/resend-verification/` | resend | Resend verification |
| `update-theme-preference/` | AJAX theme | JSON **NEEDS VERIFICATION** |

### Dashboards (`/dashboard/`)

Key routes from `dashboards/urls.py`:

- `/dashboard/user/`, `/pandit/`, `/admin-pandit/`, `/super-admin/` — role dashboards.
- Super-admin units: intelligence, SEO, crawl readiness, analytics config, feature flags, kill switch, config audit, master data, notifications hub, referrals CRUD, export, consistency checks, page edit/disable/restore, pandit suspend/reinstate, etc.
- Admin-pandit: pandit approve/reject UI, profile approve/send-back, partial block apply/remove.

### Profiles (`/profiles/`)

| Path | Purpose |
|------|---------|
| `edit/`, `edit/<public_id>/` | Edit own profile |
| `admin/pending-locations/` | Admin pending locations |
| `private/`, `private/<public_id>/` | Private profile |
| `id/<public_id>/`, `<slug:identifier>/` | Public profile |

### API Pandit (`/api/pandit/`)

| Path | Purpose |
|------|---------|
| `update-location/` | `update_pandit_location` |

### Referrals (`/referrals/`)

`generate/`, `policy/`, `policy/edit/`, `<id>/deactivate/`.

### Search

- **UI namespace** `search_ui`: `/search/…` (e.g. `results/`).
- **API namespace** `search_api`: `/api/search/…` (same `search.urls` module).

Endpoints in `search/urls.py`: `pandits/`, `suggestions/`, `trending/`, `related/`, `click/`, `recommendations/pandits/`, `results/`.

### Booking intent

- UI: `/booking-intent/…` (`history/`, `inbox/`, `create/<pandit_public_id>/`).
- API: `/api/booking-intent/…` (`api/create/`, `my-intents/`, `received-intents/`, `<public_id>/`, cancel, mark-viewed, governance list, flag).

### Reviews

- UI: `/reviews/…`
- API: `/api/reviews/…` — create, list, get, report, governance, helpful, advanced report, moderation dashboard.

### Trust display (`/api/trust-display/`)

`pandit/<id>/`, `pandit/<id>/badges/`.

### Analytics (`/api/analytics/`)

`events/`, `events/aggregated/`, `events/summary/`, `access-logs/`.

### Behavior (`/behavior/`)

`track/`, `track-event/`, `super-admin-dashboard/`.

### Notifications (`/notifications/`)

List, mark read, mark all read.

### Pages (`/pages/`)

Large surface: `create/`, `faq/`, `<page_public_id>/` detail, `<slug>/edit/`, status routes, gallery upload/delete/toggle, posts CRUD/pin/hide/delete, reviews submit, review helpful/report APIs, moderators CRUD, static CMS pages, super-admin CMS/FAQ/social dashboards under `pages/dashboard/super-admin/...`.

### Masterdata (`/masterdata/`)

Upload/toggle/download samples for geographic and pooja catalogs.

### Support (`/` include)

`contact-us/`, `support/admin/contact-requests/`.

### Branding (`/branding/`)

`manage/`, `activate/<id>/`.

### Monitoring (`/monitoring/`)

`health/`, `metrics/`.

### Admin analytics (`/admin-analytics/`)

Trending searches, top clicked pandits, top reviewed, city activity, booking stats, user engagement.

### Recommendations engine (`/recommendations/`)

`trending-pandits/`, `popular-poojas/`, `trending-searches/`, `similar-pandits/<id>/`, `recently-viewed/`.

### Feed (`/feed/`)

`feed_page`, `personalized/`.

### Ads

- Management: `/dashboard/super-admin/advertisements/` → CRUD in `ads/urls.py`.
- Tracking: `/track/ad/` → impressions, clicks, dashboards in `ads_analytics/urls.py`.

### Django admin

`/admin/` — standard Django admin.

### PWA / branding root routes

`service-worker.js`, `manifest.json` in `nityadharma/urls.py`.

---

## Section 6: OLTP vs OLAP Classification

### OLTP (transactional) — operational data

Examples: `User`, `PanditProfile`, `Page`, `BookingIntent`, `Review`, `PageReview`, `Notification`, `ReferralLink`, `ContactRequest`, `Advertisement`, governance cases, masterdata rows.

### OLAP / analytics-oriented (derived or aggregate-friendly)

| Artifact | Type | Notes |
|----------|------|-------|
| `AnalyticsEvent`, `AnalyticsAccessLog` | Hybrid | Event store; APIs expose list/aggregate/summary **NEEDS VERIFICATION** for materialized cubes. |
| `behavior_engine` daily/snapshot models | OLAP-leaning | Pre-aggregated or snapshot tables for trends, engagement, feed analytics. |
| `ads_analytics.AdDailyStats` (+ related) | OLAP-leaning | Daily/placement/location aggregates. |
| `search_*` log models | OLAP-leaning | Click/query logging for reporting. |

### OLTP → OLAP pipeline

- **Partially implemented:** Events and logs written in OLTP style; aggregation endpoints and rollup models exist for ads and behavior.
- **Not a dedicated warehouse:** No separate star-schema database or ETL tool described in-repo.

**Marking:** **Full enterprise OLAP pipeline (e.g. Snowflake/BigQuery + dbt) — NOT IMPLEMENTED** based on repository inspection.

---

## Section 7: Database Structure (Summary)

**Engine:** MySQL referenced in comments; actual connection in `dev.py`/`prod.py` — **NEEDS VERIFICATION** for live instance parameters.

### Relationship sketch (core business)

- `accounts.User` ← FK — `PanditProfile.user`, `Page.created_by`, `BookingIntent.requester` / `pandit`, `Review.user` / `pandit`, `Notification.recipient`, etc.
- `pages.Page` ← FK — `PageGalleryImage.page`, `PagePost.page`, `PageReview.page`, `PageRole.page`, `PageFollow.page`.
- `masterdata.City` / `LocalArea` ← FK from `Page` and profiles **NEEDS VERIFICATION** for all FK paths.

### Indexes

- Many models declare `db_index=True` on `public_id`, status fields, and `Meta.indexes` (e.g. `AnalyticsEvent`, ad analytics).
- **NEEDS VERIFICATION:** MySQL `EXPLAIN` on hot search/booking paths in production.

Full column-by-column DDL: **NEEDS VERIFICATION** (use `python manage.py inspectdb` or migration files against live DB; audit did not run migrations or DB).

---

## Section 8: Query Analysis (Examples)

| Operation | Example pattern | Why |
|-----------|-----------------|-----|
| Page detail gallery | `page.gallery_images.filter(is_hidden=False).order_by('-created_at')` (from `pages/views.py` context) | Public gallery hides moderated images. |
| Super admin pandit list | `User.objects.filter(role='pandit').select_related('referred_by')[:N]` | Dashboard preview with referral chain display. |
| Search | **NEEDS VERIFICATION** | Likely `filter`/`Q` objects on profiles + masterdata joins. |

**Performance concerns (generic):**

- N+1 queries if `select_related` / `prefetch_related` missing in list views — **NEEDS VERIFICATION** per view.
- Full-table scans on large log tables without time bounds — **NEEDS VERIFICATION**.

---

## Section 9: Data Flow Between Tables (Text Diagrams)

### Booking intent

```
User (requester) ----creates----> BookingIntent
                                      |
                                      v
                                 User (pandit)
```

### Page gallery

```
User (creator) ----creates----> Page
                                    |
            +-----------------------+----------------------+
            v                       v                      v
    PageGalleryImage          PagePost              PageReview
    (image FK)                (post FK)            (reviewer User FK)
```

### Pandit reviews (app `reviews`)

```
User (author) ----writes----> Review ----about----> User (pandit)
```

---

## Section 10: Dashboard Data Per Role

### User dashboard (`/dashboard/user/`)

**NEEDS VERIFICATION** for exact queryset names; typically personal summaries and links (inspect `dashboards/views.py` `dashboard_user`).

### Pandit dashboard

Pandit-scoped metrics, profile status, intents **NEEDS VERIFICATION**.

### Admin Pandit dashboard

Pending pandit counts (`User.objects.filter(role='pandit', status=...)`) patterns observed in `dashboards/views.py` grep; profile approval queues.

### Super Admin dashboard

Broader counts: users, pages, pandits, moderation widgets, SEO tools — assembled in `dashboard_super_admin` context.

**Restriction:** Super-admin-only views check `request.user.is_superuser`.

---

## Section 11: Media & File Flow

| Stage | Mechanism |
|-------|-----------|
| Upload | Django forms / admin / custom views writing `ImageField`/`FileField` under `MEDIA_ROOT`. |
| Storage | Default `FileSystemStorage` → local filesystem (Docker volume `/app/media` in typical compose). |
| URL generation | `{{ object.image.url }}` → `/media/...`. |
| Serving | Development or `SERVE_MEDIA_IN_PROD`; otherwise reverse proxy. |
| Compression | WhiteNoise compresses **static** files; **image compression pipeline for uploads** — **NEEDS VERIFICATION** (validators enforce type/size in some models). |

---

## Section 12: Security Flow

| Layer | Implementation |
|-------|----------------|
| Authentication | Django session auth; custom `User` with `EMAIL` as `USERNAME_FIELD`. |
| Authorization | Mix of `login_required`, `user_passes_test`, role checks (`role`, `is_superuser`), and per-view logic. |
| CSRF | `CsrfViewMiddleware` + tokens in forms / JS `getCookie('csrftoken')` for fetch. |
| Session hardening | `SESSION_COOKIE_HTTPONLY`, `SameSite=Lax`; secure flags **env-driven in prod** — **NEEDS VERIFICATION** in `prod.py`. |
| Deactivated users | `SessionValidationMiddleware` forces logout for deactivated accounts. |
| Public IDs | UUIDv7-style `public_id` on many entities to avoid exposing bigint PKs. |

---

## Section 13: Current Limitations / Gaps

| Item | Status |
|------|--------|
| Dedicated OLAP warehouse / ETL | **TO BE IMPLEMENTED** (no separate analytics DB observed). |
| Celery / async job runner | **TO BE IMPLEMENTED** (comments reference Celery/Django-Q; not in `INSTALLED_APPS` audit list). |
| Redis cache at scale | **Optional** — `prod.py` can enable Redis cache if `REDIS_URL` set; default `LocMem` in `base.py`. |
| Media on ephemeral disks | **Risk** — uploads lost if volume not persisted (Docker/Railway **NEEDS VERIFICATION** per deployment). |
| Full-text search DB | **NEEDS VERIFICATION** (may be MySQL `LIKE`/ORM only). |
| Rate limiting | **NEEDS VERIFICATION** (not documented in base settings excerpt). |

---

## Section 14: Future Tasks (Actionable Roadmap)

### HIGH PRIORITY

- Verify **production media serving** (`SERVE_MEDIA_IN_PROD` + nginx `/media/` + persistent volume).
- **Backup & restore** playbook for MySQL + media volume.
- Security review: ensure all JSON POST endpoints enforce CSRF + role checks (**automated test gap** — **TO BE IMPLEMENTED**).

### MEDIUM PRIORITY

- Query audit with `django-debug-toolbar` or APM on heaviest pages (search, page detail, dashboards).
- Centralize **role-based permission helpers** to reduce drift (**refactor** — out of scope for audit implementation).
- Optional **Redis** cache for session/search **NEEDS VERIFICATION** for ROI.

### LOW PRIORITY

- UI/UX consistency across dashboards.
- Expand automated documentation generation from `urlpatterns` (OpenAPI not present for HTML-first views).

---

## Section 15: Final Summary

| Dimension | Assessment |
|-----------|------------|
| **Maturity** | **Production-shaped** Django monolith with many phased modules (monitoring, analytics dashboards, behavior engine, ads). |
| **Strengths** | Clear separation of apps; public ID pattern; rich admin/super-admin tooling; intent/review/governance models documented in code. |
| **Risks** | Large attack surface (many URLs); operational complexity; media + DB backup discipline; performance under load **NEEDS VERIFICATION**. |
| **Before scaling** | Persistent media, DB replication/backups, caching/session store, background jobs for aggregates, load testing on search and page detail. |

---

## Appendix A: Model class inventory (quick reference)

`accounts`: `User`, `EmailVerificationToken`  
`pages`: `Page`, `PageGalleryImage`, `PagePost`, `PageAuditLog`, `PageReview`, `PageRole`, `PageFollow`, `PageAccessRequest`  
`profiles`: `PanditProfile`, `PendingLocation`  
`booking_intent`: `BookingIntent`  
`reviews`: `Review`  
`search`: `SavedSearch`, `SearchQueryLog`, `RelatedSearchLog`, `SearchResultClick`  
`referrals`: `ReferralLink`, `ReferralUsage`, `ReferralPolicy`  
`notifications`: `Notification`, `NotificationPreference`  
`masterdata`: `City`, `Mandal`, `LocalArea`, `PoojaCategory`, `Pooja`, `Language`, `CountryCode`, `ProfileCompletionRule`, `UploadConfig`  
`governance`: `GovernanceCase`, `GovernanceAction`, `PartialBlock`, `ApprovalRecord`, `ApprovalCustodian`  
`analytics`: `AnalyticsEvent`, `AnalyticsAccessLog`  
`ads`: `Advertisement`  
`ads_analytics`: `AdImpression`, `AdClick`, `AdConversionIntent`, `AdDailyStats`, `AdPlacementStats`, `AdLocationStats`, `AdRevenueEvent`  
`behavior_engine`: multiple event/aggregate models (see file)  
`engagement`: `UserInteractionEvent`, `PostComment`, `PostLike`  
`feed_engine`: `FeedItemCandidate`  
`core`: `AuditBase`, `TimestampBase`, `FeatureToggle`, `FeatureFlag`, `PlatformKillSwitch`  
`branding`: `BrandingLogo`  
`tracking_config`: `TrackingConfiguration`, `TrackingConfigurationAudit`  
`support`: `ContactRequest`  
`availability`: `Availability`  

---

*End of audit document.*
