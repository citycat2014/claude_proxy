"""
Automatic data cleanup module for pkts_capture.

Provides background data cleanup functionality that removes large content fields
while preserving statistical data for analysis.

Usage:
    # Manual cleanup
    from storage.cleanup import DataCleanupManager
    cleanup = DataCleanupManager(db)
    cleanup.cleanup_old_data(days=30)

    # Scheduled cleanup (runs automatically in proxy)
    from storage.cleanup import CleanupScheduler
    scheduler = CleanupScheduler(db, cleanup_manager)
    scheduler.start()
"""

import os
import sys
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, text
from storage.database import Database
from storage.models import Request, ToolCall, Message, SystemReminder, Session
from storage.recycle_bin import RecycleBinManager, CleanupLogManager
from config.settings import (
    DATA_RETENTION_DAYS,
    DATA_CLEANUP_ENABLED,
    DATA_CLEANUP_INTERVAL_HOURS,
    DATA_CLEANUP_BATCH_SIZE,
    DATABASE_PATH,
)

logger = logging.getLogger(__name__)


class DataCleanupManager:
    """
    Automatic data cleanup manager.

    Cleanup strategy:
    1. Soft delete: Only clear large content fields, preserve records and stats
    2. Time-based: Clean data older than DATA_RETENTION_DAYS
    3. Batched: Process in batches to avoid long database locks
    4. Stats preserved: token, cost, timing fields are retained
    """

    # Fields to clean (content fields that consume space)
    FIELDS_TO_CLEAN = {
        'requests': [
            'request_body',       # Raw request body (largest)
            'messages_json',      # Messages JSON
            'response_body',      # Response body
            'response_text',      # Parsed text response
            'response_thinking',  # Thinking content
        ],
        'tool_calls': [
            'tool_input_json',    # Tool input parameters
            'tool_result',        # Tool execution result
        ],
        'messages': [
            'content_text',       # Message content
        ],
    }

    # Stats fields to preserve (must remain for dashboard/statistics)
    RETAINED_STATS_FIELDS = {
        'requests': [
            'id', 'request_id', 'session_id', 'timestamp', 'method', 'endpoint',
            'model', 'system_prompt', 'response_status', 'response_time_ms', 'is_streaming',
            'input_tokens', 'output_tokens', 'cache_creation_tokens', 'cache_read_tokens',
            'cost', 'dns_ms', 'connect_ms', 'tls_ms', 'send_ms', 'wait_ms', 'receive_ms',
            'time_to_first_token_ms', 'time_to_last_token_ms', 'avg_token_latency_ms',
            'response_headers', 'x_request_id', 'ratelimit_limit', 'ratelimit_remaining',
            'ratelimit_reset', 'anthropic_version',
        ],
        'tool_calls': [
            'id', 'request_id', 'tool_name', 'timestamp',
            'timestamp_start', 'timestamp_end', 'duration_ms',
        ],
    }

    def __init__(
        self,
        db: Database,
        retention_days: int = None,
        batch_size: int = None,
        recycle_bin: RecycleBinManager = None,
        log_manager: CleanupLogManager = None,
        use_recycle_bin: bool = True
    ):
        """
        Initialize the cleanup manager.

        Args:
            db: Database instance
            retention_days: Days to retain full data (default from settings)
            batch_size: Records to process per batch (default from settings)
            recycle_bin: RecycleBinManager for moving data to recycle bin
            log_manager: CleanupLogManager for logging operations
            use_recycle_bin: Whether to use recycle bin (True) or clear fields directly (False)
        """
        self.db = db
        self.retention_days = retention_days or DATA_RETENTION_DAYS
        self.batch_size = batch_size or DATA_CLEANUP_BATCH_SIZE
        self.recycle_bin = recycle_bin
        self.log_manager = log_manager
        self.use_recycle_bin = use_recycle_bin
        self._stats = {
            'last_cleanup_time': None,
            'total_records_cleaned': 0,
            'total_space_saved_mb': 0,
        }

    def get_cleanup_stats(self) -> Dict[str, Any]:
        """
        Get statistics about cleanup operations and data that can be cleaned.

        Returns:
            Dict with cleanup stats and estimations
        """
        with self.db.db_session() as session:
            cutoff = datetime.now() - timedelta(days=self.retention_days)

            # Count old records
            old_requests = session.query(Request).filter(Request.timestamp < cutoff).count()
            old_tool_calls = session.query(ToolCall).filter(ToolCall.timestamp < cutoff).count()
            old_messages = session.query(Message).filter(Message.timestamp < cutoff).count() if hasattr(Message, 'timestamp') else 0

            # Calculate space usage of old records (approximate)
            space_info = self._estimate_space_usage(session, cutoff)

            return {
                'retention_days': self.retention_days,
                'cutoff_date': cutoff.isoformat(),
                'last_cleanup_time': self._stats['last_cleanup_time'].isoformat() if self._stats['last_cleanup_time'] else None,
                'total_records_cleaned': self._stats['total_records_cleaned'],
                'records_awaiting_cleanup': {
                    'requests': old_requests,
                    'tool_calls': old_tool_calls,
                    'messages': old_messages,
                },
                'estimated_space_to_save_mb': space_info['total_mb'],
                'space_breakdown': space_info['breakdown'],
            }

    def _estimate_space_usage(self, session, cutoff: datetime) -> Dict[str, Any]:
        """Estimate space usage of old records that can be cleaned."""
        try:
            result = session.query(
                func.count(Request.id).label('count'),
                func.sum(func.length(Request.request_body)).label('request_body'),
                func.sum(func.length(Request.messages_json)).label('messages_json'),
                func.sum(func.length(Request.response_text)).label('response_text'),
                func.sum(func.length(Request.response_thinking)).label('response_thinking'),
                func.sum(func.length(Request.response_body)).label('response_body'),
            ).filter(Request.timestamp < cutoff).first()

            breakdown = {
                'request_body_mb': (result.request_body or 0) / 1024 / 1024,
                'messages_json_mb': (result.messages_json or 0) / 1024 / 1024,
                'response_text_mb': (result.response_text or 0) / 1024 / 1024,
                'response_thinking_mb': (result.response_thinking or 0) / 1024 / 1024,
                'response_body_mb': (result.response_body or 0) / 1024 / 1024,
            }

            total_mb = sum(breakdown.values())

            return {
                'total_mb': round(total_mb, 2),
                'breakdown': {k: round(v, 2) for k, v in breakdown.items()},
            }
        except Exception as e:
            logger.warning(f"Failed to estimate space usage: {e}")
            return {'total_mb': 0, 'breakdown': {}}

    def cleanup_old_data(
        self,
        days: int = None,
        dry_run: bool = False,
        cleanup_type: str = 'manual'
    ) -> Dict[str, Any]:
        """
        Clean up old data by clearing content fields or moving to recycle bin.

        Args:
            days: Days threshold for old data (default: retention_days)
            dry_run: If True, only return stats without actually cleaning
            cleanup_type: 'auto' or 'manual' for logging

        Returns:
            Dict with cleanup results
        """
        days = days or self.retention_days
        cutoff = datetime.now() - timedelta(days=days)

        logger.info(f"Starting data cleanup for records older than {cutoff}")

        if dry_run:
            stats = self.get_cleanup_stats()
            logger.info(f"[DRY RUN] Would clean {stats['records_awaiting_cleanup']} records")
            return {'dry_run': True, **stats}

        # Start cleanup log
        log_entry = None
        if self.log_manager:
            log_entry = self.log_manager.start_cleanup_log(cleanup_type, days)

        results = {
            'cutoff_date': cutoff.isoformat(),
            'requests_cleaned': 0,
            'tool_calls_cleaned': 0,
            'messages_cleaned': 0,
            'recycle_bin_entries': 0,
            'space_reclaimed_bytes': 0,
            'errors': [],
        }

        # Clean requests
        try:
            req_count, req_space = self._cleanup_table(
                Request, 'requests', 'timestamp', cutoff, cleanup_type
            )
            results['requests_cleaned'] = req_count
            results['space_reclaimed_bytes'] += req_space
            logger.info(f"Cleaned {req_count} old requests")
        except Exception as e:
            logger.error(f"Failed to clean requests: {e}")
            results['errors'].append(f"requests: {str(e)}")

        # Clean tool calls
        try:
            tool_count, tool_space = self._cleanup_table(
                ToolCall, 'tool_calls', 'timestamp', cutoff, cleanup_type
            )
            results['tool_calls_cleaned'] = tool_count
            results['space_reclaimed_bytes'] += tool_space
            logger.info(f"Cleaned {tool_count} old tool calls")
        except Exception as e:
            logger.error(f"Failed to clean tool calls: {e}")
            results['errors'].append(f"tool_calls: {str(e)}")

        # Clean messages (if timestamp column exists)
        try:
            if hasattr(Message, 'timestamp'):
                msg_count, msg_space = self._cleanup_table(
                    Message, 'messages', 'timestamp', cutoff, cleanup_type
                )
                results['messages_cleaned'] = msg_count
                results['space_reclaimed_bytes'] += msg_space
                logger.info(f"Cleaned {msg_count} old messages")
        except Exception as e:
            logger.warning(f"Failed to clean messages: {e}")

        # Calculate total
        total_cleaned = sum([
            results['requests_cleaned'],
            results['tool_calls_cleaned'],
            results['messages_cleaned'],
        ])

        # Update stats
        self._stats['last_cleanup_time'] = datetime.now()
        self._stats['total_records_cleaned'] += total_cleaned

        # Complete cleanup log
        if self.log_manager and log_entry:
            self.log_manager.complete_cleanup_log(
                log_id=log_entry.id,
                records_processed=total_cleaned,
                records_by_table={
                    'requests': results['requests_cleaned'],
                    'tool_calls': results['tool_calls_cleaned'],
                    'messages': results['messages_cleaned'],
                },
                space_reclaimed_bytes=results['space_reclaimed_bytes'],
                recycle_bin_entries=results.get('recycle_bin_entries', 0),
                details={'errors': results['errors']} if results['errors'] else None
            )

        logger.info(f"Data cleanup completed: {results}")
        return results

    def _cleanup_table(
        self,
        model_class,
        table_name: str,
        timestamp_col: str,
        cutoff: datetime,
        cleanup_type: str = 'manual'
    ) -> Tuple[int, int]:
        """
        Clean content fields from a specific table for old records.

        Args:
            model_class: SQLAlchemy model class
            table_name: Table name for logging
            timestamp_col: Column name for timestamp filtering
            cutoff: Cutoff datetime
            cleanup_type: 'auto' or 'manual'

        Returns:
            Tuple of (number of records cleaned, space reclaimed in bytes)
        """
        fields_to_clean = self.FIELDS_TO_CLEAN.get(table_name, [])
        if not fields_to_clean:
            logger.warning(f"No fields configured for cleanup in {table_name}")
            return 0, 0

        total_cleaned = 0
        total_space = 0

        with self.db.db_session() as session:
            # Get old record IDs in batches
            while True:
                # Query batch of old records
                query = session.query(model_class).filter(
                    getattr(model_class, timestamp_col) < cutoff
                )

                # Check if any of the content fields still have data
                for field in fields_to_clean:
                    if hasattr(model_class, field):
                        query = query.filter(
                            getattr(model_class, field).isnot(None),
                            getattr(model_class, field) != ''
                        )

                records = query.limit(self.batch_size).all()

                if not records:
                    break

                # Process each record
                for record in records:
                    # Extract content fields
                    content_data = {}
                    for field in fields_to_clean:
                        if hasattr(record, field):
                            value = getattr(record, field)
                            if value:
                                content_data[field] = value

                    # Calculate space
                    content_size = len(json.dumps(content_data).encode('utf-8'))
                    total_space += content_size

                    # Move to recycle bin if enabled
                    if self.use_recycle_bin and self.recycle_bin and content_data:
                        metadata = {
                            'request_id': getattr(record, 'request_id', None),
                            'session_id': getattr(record, 'session_id', None),
                        }
                        self.recycle_bin.move_to_recycle_bin(
                            table_name=table_name,
                            record_id=record.id,
                            content_fields=content_data,
                            metadata=metadata,
                            cleanup_type=cleanup_type
                        )

                    # Clear content fields
                    for field in fields_to_clean:
                        if hasattr(record, field):
                            setattr(record, field, '')

                session.commit()
                total_cleaned += len(records)

                if len(records) < self.batch_size:
                    break

        return total_cleaned, total_space

    def vacuum_database(self) -> bool:
        """
        Run VACUUM to reclaim database space.

        Note: This requires exclusive access to the database.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Running database VACUUM...")
            with self.db.db_session() as session:
                session.execute(text("VACUUM"))
            logger.info("Database VACUUM completed")
            return True
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
            return False


class CleanupScheduler:
    """
    Background cleanup scheduler that runs cleanup tasks periodically.

    Features:
    - Scheduled execution: Runs at configured intervals
    - Idle detection: Avoids running during peak hours
    - Progress tracking: Records last cleanup time
    - Graceful shutdown: Safely stops on program exit
    """

    def __init__(
        self,
        db: Database,
        cleanup_manager: DataCleanupManager = None,
        interval_hours: int = None,
        recycle_bin: RecycleBinManager = None,
        log_manager: CleanupLogManager = None,
        settings_manager = None
    ):
        """
        Initialize the cleanup scheduler.

        Args:
            db: Database instance
            cleanup_manager: DataCleanupManager instance (created if None)
            interval_hours: Hours between cleanup runs (default from settings)
            recycle_bin: RecycleBinManager for moving data to recycle bin
            log_manager: CleanupLogManager for logging operations
            settings_manager: SettingsManager for dynamic configuration
        """
        self.db = db
        self.interval_hours = interval_hours or DATA_CLEANUP_INTERVAL_HOURS
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_cleanup_time: Optional[datetime] = None
        self._running = False
        self.settings_manager = settings_manager

        # Create managers if not provided
        if cleanup_manager is None:
            use_recycle_bin = True
            if settings_manager:
                use_recycle_bin = settings_manager.get_setting('recycle_bin_enabled', True)
            self.cleanup = DataCleanupManager(
                db,
                recycle_bin=recycle_bin,
                log_manager=log_manager,
                use_recycle_bin=use_recycle_bin
            )
        else:
            self.cleanup = cleanup_manager

    def start(self):
        """Start the background cleanup thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Cleanup scheduler already running")
            return

        # Check if cleanup is enabled (from settings or env)
        cleanup_enabled = DATA_CLEANUP_ENABLED
        if self.settings_manager:
            cleanup_enabled = self.settings_manager.get_setting('cleanup_enabled', DATA_CLEANUP_ENABLED)

        if not cleanup_enabled:
            logger.info("Data cleanup is disabled in settings")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="DataCleanupScheduler"
        )
        self._thread.start()
        self._running = True
        logger.info(
            f"Cleanup scheduler started (interval={self.interval_hours}h, "
            f"retention={self.cleanup.retention_days}d)"
        )

    def stop(self, timeout: float = 10.0):
        """
        Stop the cleanup scheduler.

        Args:
            timeout: Maximum seconds to wait for thread to finish
        """
        if self._thread is None:
            return

        logger.info("Stopping cleanup scheduler...")
        self._stop_event.set()
        self._thread.join(timeout=timeout)

        if self._thread.is_alive():
            logger.warning("Cleanup scheduler thread did not terminate cleanly")

        self._thread = None
        self._running = False
        logger.info("Cleanup scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running and self._thread is not None and self._thread.is_alive()

    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        # Check if cleanup is enabled
        cleanup_enabled = DATA_CLEANUP_ENABLED
        if self.settings_manager:
            cleanup_enabled = self.settings_manager.get_setting('cleanup_enabled', DATA_CLEANUP_ENABLED)

        return {
            'running': self.is_running(),
            'enabled': cleanup_enabled,
            'interval_hours': self.interval_hours,
            'last_cleanup_time': self._last_cleanup_time.isoformat() if self._last_cleanup_time else None,
            'next_cleanup_time': self._get_next_cleanup_time().isoformat() if self._get_next_cleanup_time() else None,
        }

    def _get_next_cleanup_time(self) -> Optional[datetime]:
        """Calculate next scheduled cleanup time."""
        if not self._last_cleanup_time:
            return None
        return self._last_cleanup_time + timedelta(hours=self.interval_hours)

    def _cleanup_loop(self):
        """Main scheduler loop."""
        # Initial delay before first check (5 minutes after startup)
        initial_delay = 300  # 5 minutes
        logger.info(f"Cleanup scheduler: waiting {initial_delay}s before first check")

        if self._stop_event.wait(initial_delay):
            return

        while not self._stop_event.is_set():
            try:
                # Check if cleanup is still enabled (dynamic config)
                if self.settings_manager:
                    cleanup_enabled = self.settings_manager.get_setting('cleanup_enabled', True)
                    if not cleanup_enabled:
                        logger.debug("Cleanup disabled, skipping this cycle")
                        # Wait 1 hour and check again
                        for _ in range(3600):
                            if self._stop_event.is_set():
                                return
                            time.sleep(1)
                        continue

                    # Update interval from settings
                    self.interval_hours = self.settings_manager.get_setting(
                        'cleanup_interval_hours', DATA_CLEANUP_INTERVAL_HOURS
                    )

                if self._should_run_cleanup():
                    logger.info("Starting scheduled data cleanup")
                    results = self.cleanup.cleanup_old_data(cleanup_type='auto')
                    self._last_cleanup_time = datetime.now()

                    # Log summary
                    total_cleaned = sum([
                        results.get('requests_cleaned', 0),
                        results.get('tool_calls_cleaned', 0),
                        results.get('messages_cleaned', 0),
                    ])
                    logger.info(f"Scheduled cleanup completed: {total_cleaned} records cleaned")

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

            # Wait for next interval (check every hour)
            for _ in range(3600):  # 3600 seconds = 1 hour
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _should_run_cleanup(self) -> bool:
        """
        Determine if cleanup should run based on schedule.

        Returns:
            True if cleanup should run, False otherwise
        """
        # Check if enough time has passed since last cleanup
        if self._last_cleanup_time is None:
            return True

        next_cleanup = self._last_cleanup_time + timedelta(hours=self.interval_hours)
        return datetime.now() >= next_cleanup


# Convenience functions for one-off cleanup
def run_cleanup_now(db: Database = None, days: int = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    Run cleanup immediately (one-time execution).

    Args:
        db: Database instance (creates new if None)
        days: Retention days (uses settings if None)
        dry_run: If True, only show stats without cleaning

    Returns:
        Cleanup results dict
    """
    if db is None:
        db = Database()

    cleanup = DataCleanupManager(db, retention_days=days)
    return cleanup.cleanup_old_data(days=days, dry_run=dry_run)


def get_cleanup_status(db: Database = None) -> Dict[str, Any]:
    """
    Get current cleanup status and statistics.

    Args:
        db: Database instance (creates new if None)

    Returns:
        Status dict
    """
    if db is None:
        db = Database()

    cleanup = DataCleanupManager(db)
    return cleanup.get_cleanup_stats()


if __name__ == "__main__":
    # CLI interface for manual cleanup
    import argparse

    parser = argparse.ArgumentParser(description="Data cleanup utility")
    parser.add_argument("--days", type=int, default=None, help="Retention days")
    parser.add_argument("--dry-run", action="store_true", help="Show stats without cleaning")
    parser.add_argument("--stats", action="store_true", help="Show cleanup statistics")
    parser.add_argument("--vacuum", action="store_true", help="Run VACUUM after cleanup")

    args = parser.parse_args()

    db = Database()

    if args.stats:
        stats = get_cleanup_status(db)
        print("\nCleanup Statistics:")
        print(f"  Retention: {stats['retention_days']} days")
        print(f"  Cutoff date: {stats['cutoff_date']}")
        print(f"  Last cleanup: {stats['last_cleanup_time'] or 'Never'}")
        print(f"\nRecords awaiting cleanup:")
        for table, count in stats['records_awaiting_cleanup'].items():
            print(f"    {table}: {count}")
        print(f"\nEstimated space to save: {stats['estimated_space_to_save_mb']:.1f} MB")

    else:
        print(f"Running cleanup (dry_run={args.dry_run})...")
        results = run_cleanup_now(db, days=args.days, dry_run=args.dry_run)
        print(f"\nResults:")
        print(f"  Requests cleaned: {results.get('requests_cleaned', 0)}")
        print(f"  Tool calls cleaned: {results.get('tool_calls_cleaned', 0)}")
        print(f"  Messages cleaned: {results.get('messages_cleaned', 0)}")

        if args.vacuum and not args.dry_run:
            cleanup = DataCleanupManager(db)
            cleanup.vacuum_database()
