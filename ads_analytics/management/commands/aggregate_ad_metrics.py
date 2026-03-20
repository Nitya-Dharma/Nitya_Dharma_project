"""
Management command to run daily ad metrics aggregation.

Usage:
  python manage.py aggregate_ad_metrics
  python manage.py aggregate_ad_metrics --date 2025-01-15
  python manage.py aggregate_ad_metrics --days 7
"""

import logging
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from ads_analytics.aggregation import aggregate_daily_ad_metrics
from ads_analytics.services.dashboard_service import invalidate_dashboard_cache

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Aggregate ad impressions and clicks into daily stats (AdDailyStats, AdPlacementStats, AdLocationStats)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Target date YYYY-MM-DD (default: today)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Number of days to aggregate (default: 1)",
        )

    def handle(self, *args, **options):
        target_date = None
        if options["date"]:
            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                self.stderr.write(self.style.ERROR("Invalid --date; use YYYY-MM-DD"))
                return
        if target_date is None:
            target_date = timezone.now().date()

        days = max(1, options["days"])
        logger.info("aggregate_ad_metrics command start: target_date=%s, days=%s", target_date, days)
        self.stdout.write(f"Aggregating ad metrics for {target_date} (days={days})...")
        result = aggregate_daily_ad_metrics(target_date=target_date, days=days)
        logger.info(
            "aggregate_ad_metrics command complete: ad_daily_stats=%s, placement_stats=%s, location_stats=%s",
            result["ad_daily_stats"],
            result["placement_stats"],
            result["location_stats"],
        )
        invalidate_dashboard_cache()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {result['ad_daily_stats']} ad daily rows, "
                f"{result['placement_stats']} placement rows, "
                f"{result['location_stats']} location rows."
            )
        )
