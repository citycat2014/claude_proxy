"""
Recycle bin management module for pkts_capture.

Provides functionality for:
- Moving cleaned data to recycle bin
- Managing recycle bin entries
- Cleanup logging
- System settings management
"""

import os
import sys
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, desc
from storage.database import Database
from storage.models import (
    RecycleBin, CleanupLog, SystemSetting,
    Request, ToolCall, Message
)

logger = logging.getLogger(__name__)


class RecycleBinManager:
    """
    Manages recycle bin operations.

    Features:
    - Move data to recycle bin (instead of clearing fields)
    - List/filter recycle bin entries
    - Permanent delete from recycle bin
    - Auto-expire old entries
    """

    DEFAULT_RETENTION_DAYS = 7

    def __init__(self, db: Database, retention_days: int = None):
        """
        Initialize the recycle bin manager.

        Args:
            db: Database instance
            retention_days: Days to keep data in recycle bin before auto-delete
        """
        self.db = db
        self.retention_days = retention_days or self.DEFAULT_RETENTION_DAYS

    def move_to_recycle_bin(
        self,
        table_name: str,
        record_id: int,
        content_fields: Dict[str, str],
        metadata: Dict[str, Any],
        cleanup_type: str = 'auto'
    ) -> Optional[RecycleBin]:
        """
        Move record content to recycle bin.

        Args:
            table_name: Original table name ('requests', 'tool_calls', etc.)
            record_id: Original record ID
            content_fields: Dict of field_name -> field_value to store
            metadata: Additional metadata (request_id, session_id, etc.)
            cleanup_type: 'auto' or 'manual'

        Returns:
            Created RecycleBin entry or None if failed
        """
        try:
            # Calculate content size
            content_json = json.dumps(content_fields)
            content_size = len(content_json.encode('utf-8'))

            # Calculate expiration date
            expires_at = datetime.now() + timedelta(days=self.retention_days)

            # Create recycle bin entry
            entry = RecycleBin(
                original_table=table_name,
                original_id=record_id,
                request_id=metadata.get('request_id'),
                session_id=metadata.get('session_id'),
                content_data=content_json,
                content_size_bytes=content_size,
                expires_at=expires_at,
                cleanup_type=cleanup_type,
            )

            with self.db.db_session() as session:
                session.add(entry)
                session.commit()
                # Refresh to get the ID
                session.refresh(entry)

            logger.debug(f"Moved {table_name}.{record_id} to recycle bin (size: {content_size} bytes)")
            return entry

        except Exception as e:
            logger.error(f"Failed to move to recycle bin: {e}")
            return None

    def get_recycle_bin_entries(
        self,
        table_filter: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[RecycleBin], int]:
        """
        Get recycle bin entries with pagination.

        Args:
            table_filter: Filter by original table name
            limit: Number of records per page
            offset: Offset for pagination

        Returns:
            Tuple of (entries list, total count)
        """
        with self.db.db_session() as session:
            query = session.query(RecycleBin)

            if table_filter:
                query = query.filter(RecycleBin.original_table == table_filter)

            # Order by cleaned_at desc (newest first)
            query = query.order_by(desc(RecycleBin.cleaned_at))

            # Get total count
            total = query.count()

            # Get paginated results
            entries = query.offset(offset).limit(limit).all()

            return entries, total

    def get_recycle_bin_entry(self, entry_id: int) -> Optional[RecycleBin]:
        """Get a single recycle bin entry by ID."""
        with self.db.db_session() as session:
            return session.query(RecycleBin).filter(RecycleBin.id == entry_id).first()

    def permanent_delete(self, entry_id: int) -> bool:
        """
        Permanently delete a recycle bin entry.

        Args:
            entry_id: Recycle bin entry ID

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db.db_session() as session:
                entry = session.query(RecycleBin).filter(RecycleBin.id == entry_id).first()
                if entry:
                    session.delete(entry)
                    session.commit()
                    logger.debug(f"Permanently deleted recycle bin entry {entry_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete recycle bin entry {entry_id}: {e}")
            return False

    def permanent_delete_batch(
        self,
        entry_ids: List[int] = None,
        older_than_days: int = None
    ) -> int:
        """
        Batch delete from recycle bin.

        Args:
            entry_ids: Specific IDs to delete (if None, use older_than_days)
            older_than_days: Delete entries older than N days

        Returns:
            Number of entries deleted
        """
        try:
            with self.db.db_session() as session:
                if entry_ids:
                    # Delete specific entries
                    deleted = session.query(RecycleBin).filter(
                        RecycleBin.id.in_(entry_ids)
                    ).delete(synchronize_session=False)
                elif older_than_days:
                    # Delete entries older than specified days
                    cutoff = datetime.now() - timedelta(days=older_than_days)
                    deleted = session.query(RecycleBin).filter(
                        RecycleBin.cleaned_at < cutoff
                    ).delete(synchronize_session=False)
                else:
                    return 0

                session.commit()
                logger.info(f"Permanently deleted {deleted} recycle bin entries")
                return deleted

        except Exception as e:
            logger.error(f"Failed to batch delete recycle bin entries: {e}")
            return 0

    def clear_recycle_bin(self) -> int:
        """
        Clear all entries from recycle bin.

        Returns:
            Number of entries deleted
        """
        return self.permanent_delete_batch(entry_ids=None, older_than_days=0)

    def auto_expire_old_entries(self) -> int:
        """
        Auto-delete entries past expiration date.

        Returns:
            Number of entries deleted
        """
        try:
            with self.db.db_session() as session:
                deleted = session.query(RecycleBin).filter(
                    RecycleBin.expires_at < datetime.now()
                ).delete(synchronize_session=False)
                session.commit()

                if deleted > 0:
                    logger.info(f"Auto-expired {deleted} old recycle bin entries")
                return deleted
        except Exception as e:
            logger.error(f"Failed to auto-expire recycle bin entries: {e}")
            return 0

    def get_recycle_bin_stats(self) -> Dict[str, Any]:
        """
        Get recycle bin statistics.

        Returns:
            Dict with statistics
        """
        with self.db.db_session() as session:
            # Total entries
            total_entries = session.query(RecycleBin).count()

            # Total size
            total_size = session.query(
                func.sum(RecycleBin.content_size_bytes)
            ).scalar() or 0

            # Entries by table
            by_table = session.query(
                RecycleBin.original_table,
                func.count(RecycleBin.id).label('count'),
                func.sum(RecycleBin.content_size_bytes).label('size')
            ).group_by(RecycleBin.original_table).all()

            # Expiring soon (within 24 hours)
            soon = datetime.now() + timedelta(hours=24)
            expiring_soon = session.query(RecycleBin).filter(
                RecycleBin.expires_at < soon
            ).count()

            return {
                'total_entries': total_entries,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'by_table': [
                    {
                        'table': t,
                        'count': c,
                        'size_mb': round(s / 1024 / 1024, 2) if s else 0
                    }
                    for t, c, s in by_table
                ],
                'expiring_soon': expiring_soon,
                'retention_days': self.retention_days,
            }


class CleanupLogManager:
    """Manages cleanup log operations."""

    def __init__(self, db: Database):
        """
        Initialize the cleanup log manager.

        Args:
            db: Database instance
        """
        self.db = db

    def start_cleanup_log(self, cleanup_type: str, retention_days: int = None) -> CleanupLog:
        """
        Start a new cleanup log entry.

        Args:
            cleanup_type: 'auto', 'manual', or 'recycle_bin_purge'
            retention_days: Retention days used for this cleanup

        Returns:
            Created CleanupLog entry
        """
        log = CleanupLog(
            cleanup_type=cleanup_type,
            retention_days=retention_days,
        )

        with self.db.db_session() as session:
            session.add(log)
            session.commit()
            session.refresh(log)

        logger.debug(f"Started cleanup log {log.id} (type: {cleanup_type})")
        return log

    def complete_cleanup_log(
        self,
        log_id: int,
        records_processed: int,
        records_by_table: Dict[str, int],
        space_reclaimed_bytes: int = 0,
        recycle_bin_entries: int = 0,
        details: Dict[str, Any] = None
    ):
        """
        Complete a cleanup log entry.

        Args:
            log_id: Log entry ID
            records_processed: Total records processed
            records_by_table: Dict of table_name -> count
            space_reclaimed_bytes: Space reclaimed in bytes
            recycle_bin_entries: Number of entries moved to recycle bin
            details: Additional details dict
        """
        try:
            with self.db.db_session() as session:
                log = session.query(CleanupLog).filter(CleanupLog.id == log_id).first()
                if log:
                    log.records_processed = records_processed
                    log.records_by_table = json.dumps(records_by_table)
                    log.space_reclaimed_bytes = space_reclaimed_bytes
                    log.recycle_bin_entries = recycle_bin_entries
                    log.completed_at = datetime.now()
                    if details:
                        log.details = json.dumps(details)
                    session.commit()
                    logger.debug(f"Completed cleanup log {log_id}")
        except Exception as e:
            logger.error(f"Failed to complete cleanup log {log_id}: {e}")

    def get_cleanup_logs(
        self,
        cleanup_type: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[CleanupLog], int]:
        """
        Get cleanup logs with pagination.

        Args:
            cleanup_type: Filter by type ('auto', 'manual', 'recycle_bin_purge')
            limit: Number of records per page
            offset: Offset for pagination

        Returns:
            Tuple of (logs list, total count)
        """
        with self.db.db_session() as session:
            query = session.query(CleanupLog)

            if cleanup_type:
                query = query.filter(CleanupLog.cleanup_type == cleanup_type)

            # Order by started_at desc (newest first)
            query = query.order_by(desc(CleanupLog.started_at))

            total = query.count()
            logs = query.offset(offset).limit(limit).all()

            return logs, total

    def get_cleanup_stats(self) -> Dict[str, Any]:
        """
        Get overall cleanup statistics.

        Returns:
            Dict with statistics
        """
        with self.db.db_session() as session:
            # Total cleanups
            total_cleanups = session.query(CleanupLog).count()

            # By type
            by_type = session.query(
                CleanupLog.cleanup_type,
                func.count(CleanupLog.id).label('count')
            ).group_by(CleanupLog.cleanup_type).all()

            # Total records processed
            total_records = session.query(
                func.sum(CleanupLog.records_processed)
            ).scalar() or 0

            # Total space reclaimed
            total_space = session.query(
                func.sum(CleanupLog.space_reclaimed_bytes)
            ).scalar() or 0

            # Recent cleanups (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            recent = session.query(CleanupLog).filter(
                CleanupLog.started_at > week_ago
            ).count()

            return {
                'total_cleanups': total_cleanups,
                'by_type': {t: c for t, c in by_type},
                'total_records_processed': int(total_records),
                'total_space_reclaimed_bytes': int(total_space),
                'total_space_reclaimed_mb': round(total_space / 1024 / 1024, 2),
                'recent_cleanups_7d': recent,
            }


class SettingsManager:
    """Manages system settings that can be modified at runtime."""

    DEFAULT_SETTINGS = {
        'data_retention_days': {
            'value': '30',
            'type': 'int',
            'description': 'Days to retain full data before cleanup',
        },
        'recycle_bin_retention_days': {
            'value': '7',
            'type': 'int',
            'description': 'Days to keep data in recycle bin',
        },
        'cleanup_interval_hours': {
            'value': '24',
            'type': 'int',
            'description': 'Hours between cleanup checks',
        },
        'cleanup_enabled': {
            'value': 'true',
            'type': 'bool',
            'description': 'Enable automatic data cleanup',
        },
        'recycle_bin_enabled': {
            'value': 'true',
            'type': 'bool',
            'description': 'Enable recycle bin (move to bin instead of delete)',
        },
    }

    def __init__(self, db: Database):
        """
        Initialize the settings manager.

        Args:
            db: Database instance
        """
        self.db = db
        self._ensure_default_settings()

    def _ensure_default_settings(self):
        """Ensure default settings exist in database."""
        with self.db.db_session() as session:
            for key, config in self.DEFAULT_SETTINGS.items():
                existing = session.query(SystemSetting).filter(
                    SystemSetting.key == key
                ).first()

                if not existing:
                    setting = SystemSetting(
                        key=key,
                        value=config['value'],
                        value_type=config['type'],
                        description=config['description'],
                    )
                    session.add(setting)

            session.commit()

    def get_setting(self, key: str, default=None) -> Any:
        """
        Get a setting value.

        Args:
            key: Setting key
            default: Default value if not found

        Returns:
            Setting value with proper type
        """
        with self.db.db_session() as session:
            setting = session.query(SystemSetting).filter(
                SystemSetting.key == key
            ).first()

            if setting:
                return setting.get_typed_value()
            return default

    def set_setting(self, key: str, value: Any, value_type: str = None) -> bool:
        """
        Update a setting value.

        Args:
            key: Setting key
            value: New value
            value_type: Value type ('str', 'int', 'bool', 'float'), auto-detected if None

        Returns:
            True if successful
        """
        try:
            # Auto-detect type
            if value_type is None:
                if isinstance(value, bool):
                    value_type = 'bool'
                elif isinstance(value, int):
                    value_type = 'int'
                elif isinstance(value, float):
                    value_type = 'float'
                else:
                    value_type = 'str'

            with self.db.db_session() as session:
                setting = session.query(SystemSetting).filter(
                    SystemSetting.key == key
                ).first()

                if setting:
                    setting.value = str(value)
                    setting.value_type = value_type
                    setting.updated_at = datetime.now()
                    session.commit()
                    logger.debug(f"Updated setting {key} = {value}")
                    return True
                else:
                    logger.warning(f"Setting {key} not found")
                    return False

        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False

    def get_all_settings(self) -> List[SystemSetting]:
        """Get all settings."""
        with self.db.db_session() as session:
            return session.query(SystemSetting).order_by(SystemSetting.key).all()

    def get_cleanup_settings(self) -> Dict[str, Any]:
        """
        Get all cleanup-related settings.

        Returns:
            Dict with cleanup settings
        """
        return {
            'data_retention_days': self.get_setting('data_retention_days', 30),
            'recycle_bin_retention_days': self.get_setting('recycle_bin_retention_days', 7),
            'cleanup_interval_hours': self.get_setting('cleanup_interval_hours', 24),
            'cleanup_enabled': self.get_setting('cleanup_enabled', True),
            'recycle_bin_enabled': self.get_setting('recycle_bin_enabled', True),
        }
