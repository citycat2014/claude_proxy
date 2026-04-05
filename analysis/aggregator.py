"""
Statistics aggregator for pre-computing hourly and daily snapshots.

Runs periodically to aggregate request data into the statistics table,
avoiding full table scans on dashboard queries.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func

from storage.database import Database
from storage.models import Statistics, Request

logger = logging.getLogger(__name__)


class StatisticsAggregator:
    """
    Pre-computes statistics snapshots.

    Aggregates request data into hourly and daily summaries
    for fast dashboard queries.
    """

    def __init__(self, db: Database):
        self.db = db

    def aggregate_hour(self, hour_start: datetime) -> Optional[Statistics]:
        """
        Aggregate statistics for a specific hour.

        Args:
            hour_start: Start of the hour to aggregate

        Returns:
            Statistics record or None if no data
        """
        hour_end = hour_start + timedelta(hours=1)

        with self.db.db_session() as session:
            # Check if already aggregated
            existing = session.query(Statistics).filter_by(
                period_type='hour',
                period_start=hour_start
            ).first()

            if existing:
                # Recalculate existing record
                logger.info(f"Re-aggregating hour {hour_start}")
            else:
                logger.info(f"Aggregating hour {hour_start}")

            # Query aggregates for this hour using func
            result = session.query(
                func.count(Request.id).label('request_count'),
                func.sum(Request.input_tokens).label('total_input_tokens'),
                func.sum(Request.output_tokens).label('total_output_tokens'),
                func.sum(Request.cost).label('total_cost'),
                func.avg(Request.response_time_ms).label('avg_response_time_ms')
            ).filter(
                Request.timestamp >= hour_start,
                Request.timestamp < hour_end
            ).first()

            if not result or result.request_count == 0:
                # No data for this hour
                if existing:
                    # Delete empty existing record
                    session.delete(existing)
                    session.commit()
                return None

            # Calculate average response time
            avg_response_time = result.avg_response_time_ms if result else None

            # Sum tokens and cost (handle None values)
            total_input = result.total_input_tokens or 0
            total_output = result.total_output_tokens or 0
            total_cost = result.total_cost or 0

            if existing:
                existing.request_count = result.request_count
                existing.total_input_tokens = total_input
                existing.total_output_tokens = total_output
                existing.total_cost = total_cost
                existing.avg_response_time_ms = avg_response_time
                stats = existing
            else:
                stats = Statistics(
                    period_type='hour',
                    period_start=hour_start,
                    request_count=result.request_count,
                    total_input_tokens=total_input,
                    total_output_tokens=total_output,
                    total_cost=total_cost,
                    avg_response_time_ms=avg_response_time,
                )
                session.add(stats)

            session.commit()
            return stats

    def aggregate_day(self, day_start: datetime) -> Optional[Statistics]:
        """
        Aggregate statistics for a specific day.

        Args:
            day_start: Start of the day to aggregate

        Returns:
            Statistics record or None if no data
        """
        day_end = day_start + timedelta(days=1)

        with self.db.db_session() as session:
            # Check if already aggregated
            existing = session.query(Statistics).filter_by(
                period_type='day',
                period_start=day_start
            ).first()

            if existing:
                logger.info(f"Re-aggregating day {day_start}")
            else:
                logger.info(f"Aggregating day {day_start}")

            # Query aggregates for this day using func
            result = session.query(
                func.count(Request.id).label('request_count'),
                func.sum(Request.input_tokens).label('total_input_tokens'),
                func.sum(Request.output_tokens).label('total_output_tokens'),
                func.sum(Request.cost).label('total_cost'),
                func.avg(Request.response_time_ms).label('avg_response_time_ms')
            ).filter(
                Request.timestamp >= day_start,
                Request.timestamp < day_end
            ).first()

            if not result or result.request_count == 0:
                if existing:
                    session.delete(existing)
                    session.commit()
                return None

            request_count = result.request_count
            total_input = result.total_input_tokens or 0
            total_output = result.total_output_tokens or 0
            total_cost = result.total_cost or 0
            avg_response_time = result.avg_response_time_ms

            if request_count == 0:
                if existing:
                    session.delete(existing)
                    session.commit()
                return None

            if existing:
                existing.request_count = request_count
                existing.total_input_tokens = total_input
                existing.total_output_tokens = total_output
                existing.total_cost = total_cost
                existing.avg_response_time_ms = avg_response_time
                stats = existing
            else:
                stats = Statistics(
                    period_type='day',
                    period_start=day_start,
                    request_count=request_count,
                    total_input_tokens=total_input,
                    total_output_tokens=total_output,
                    total_cost=total_cost,
                    avg_response_time_ms=avg_response_time,
                )
                session.add(stats)

            session.commit()
            return stats

    def aggregate_missing_hours(self) -> int:
        """
        Aggregate all hours that haven't been aggregated yet.

        Returns:
            Number of hours aggregated
        """
        with self.db.db_session() as session:
            # Get earliest and latest request timestamps
            from sqlalchemy import func
            min_max = session.query(
                func.min(Request.timestamp),
                func.max(Request.timestamp)
            ).first()

            if not min_max or not min_max[0]:
                return 0

            min_time = min_max[0]
            max_time = min_max[1]

            # Get already aggregated hours
            aggregated = session.query(Statistics.period_start).filter_by(
                period_type='hour'
            ).all()
            aggregated_hours = {r[0].replace(minute=0, second=0, microsecond=0) for r in aggregated}

            count = 0
            current = min_time.replace(minute=0, second=0, microsecond=0)

            while current <= max_time:
                if current not in aggregated_hours:
                    try:
                        self.aggregate_hour(current)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error aggregating hour {current}: {e}")
                current += timedelta(hours=1)

            return count

    def update_latest_hour(self) -> Optional[Statistics]:
        """
        Update statistics for the current (in-progress) hour.

        Returns:
            Statistics record or None
        """
        now = datetime.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        return self.aggregate_hour(current_hour)

    def update_latest_day(self) -> Optional[Statistics]:
        """
        Update statistics for the current (in-progress) day.

        Returns:
            Statistics record or None
        """
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return self.aggregate_day(today)


# Convenience functions for use in worker/cron

def init_statistics_aggregator(db: Database) -> StatisticsAggregator:
    """Initialize statistics aggregator."""
    return StatisticsAggregator(db)


def run_hourly_aggregation(db: Database) -> Optional[Statistics]:
    """Run aggregation for the current hour."""
    aggregator = StatisticsAggregator(db)
    return aggregator.update_latest_hour()


def run_daily_aggregation(db: Database) -> Optional[Statistics]:
    """Run aggregation for the previous day (called at start of new day)."""
    aggregator = StatisticsAggregator(db)
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    return aggregator.aggregate_day(yesterday_start)
