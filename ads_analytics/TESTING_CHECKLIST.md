# Advertisement Analytics — Testing Checklist

Use this after implementing the analytics foundation. **Existing ad placement and serving logic must remain unchanged.**

## Phase 1 – Event models

- [ ] Run migrations: `python manage.py migrate ads_analytics`
- [ ] Confirm tables exist: `AdImpression`, `AdClick`, `AdConversionIntent`, `AdDailyStats`, `AdPlacementStats`, `AdLocationStats`, `AdRevenueEvent`

## Phase 2 – Tracking

- [ ] Load a page that shows ads (e.g. homepage with top/sidebar/footer). Confirm `AdImpression` rows are created (check admin or DB).
- [ ] Click an image ad. Confirm redirect goes to the advertiser URL and that an `AdClick` row is created.
- [ ] Confirm session_id and (when logged in) user_id are set on impression/click.
- [ ] Confirm page load time is not noticeably increased (tracking is a single insert per ad).

## Phase 3 – Aggregation

- [ ] Run: `python manage.py aggregate_ad_metrics`
- [ ] Run: `python manage.py aggregate_ad_metrics --days 7`
- [ ] Confirm `AdDailyStats`, `AdPlacementStats`, and `AdLocationStats` rows exist for the aggregated dates.

## Phase 4 – Dashboard queries

- [ ] Call `ads_analytics.queries.advertiser_kpis(ad_id, days=30)` and confirm structure (impressions, clicks, CTR, top_placements, etc.).
- [ ] Call `ads_analytics.queries.pandit_ad_kpis(pandit_id, days=30)` when you have impressions on a pandit profile.
- [ ] Call `ads_analytics.queries.platform_ad_kpis(days=30)` and confirm total impressions, clicks, placement performance, top cities.

## Phase 5 – Revenue (optional)

- [ ] Call `ads_analytics.services.record_ad_revenue_event(ad_id, "CPM", impressions=1000, revenue_amount=50.0)` and confirm `AdRevenueEvent` row.

## Regression

- [ ] Ads still display in the same positions (top, sidebar, footer, etc.).
- [ ] Image and script ads render correctly.
- [ ] No errors in logs when loading pages with ads or when clicking ads.
