#!/usr/bin/env python3
"""
Periodic statistics aggregation task.

Run this script periodically (e.g., via cron) to keep statistics up to date.

Usage:
    # Aggregate latest hour
    python scripts/aggregate_stats.py --hourly

    # Aggregate previous day
    python scripts/aggregate_stats.py --daily

    # Aggregate all missing hours
    python scripts/aggregate_stats.py --backfill
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import Database
from config.settings import DATABASE_PATH
from analysis.aggregator import StatisticsAggregator


def main():
    parser = argparse.ArgumentParser(description="Aggregate statistics")
    parser.add_argument("--hourly", action="store_true", help="Aggregate current hour")
    parser.add_argument("--daily", action="store_true", help="Aggregate previous day")
    parser.add_argument("--backfill", action="store_true", help="Backfill all missing hours")
    args = parser.parse_args()

    db = Database(DATABASE_PATH)
    aggregator = StatisticsAggregator(db)

    if args.hourly:
        print(f"Aggregating current hour...")
        stats = aggregator.update_latest_hour()
        if stats:
            print(f"✓ Aggregated {stats.request_count} requests")
        else:
            print("No data to aggregate")

    if args.daily:
        print(f"Aggregating previous day...")
        stats = aggregator.update_latest_day()
        if stats:
            print(f"✓ Aggregated {stats.request_count} requests")
        else:
            print("No data to aggregate")

    if args.backfill:
        print(f"Backfilling missing hours...")
        count = aggregator.aggregate_missing_hours()
        print(f"✓ Aggregated {count} hours")


if __name__ == "__main__":
    main()
