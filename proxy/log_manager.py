"""
Log Manager for rotating log files.

Features:
- Separate log files for proxy runtime logs and request details
- Daily rotation with date-based naming
- Automatic cleanup of logs older than 7 days
"""

import json
import logging
import os
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


class RotatingFileHandler(TimedRotatingFileHandler):
    """
    Custom rotating file handler that keeps logs for a fixed number of days.

    Extends TimedRotatingFileHandler with automatic cleanup of old log files.
    """

    def __init__(self, filename: str, retention_days: int = 7, when: str = 'D',
                 interval: int = 1, suffix: str = '%Y-%m-%d', **kwargs):
        # Set the suffix for the rotated filename
        super().__init__(
            filename,
            when=when,
            interval=interval,
            backupCount=retention_days,
            encoding='utf-8',
            **kwargs
        )
        self.retention_days = retention_days
        self.log_dir = Path(filename).parent
        # Override the suffix (TimedRotatingFileHandler uses self.suffix for naming)
        self.suffix = suffix

    def doRollover(self):
        """Perform rollover and cleanup of old logs."""
        super().doRollover()
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        """Remove log files older than retention_days."""
        if not self.log_dir.exists():
            return

        cutoff = datetime.now() - timedelta(days=self.retention_days)

        # Match files like proxy.log.2026-04-01
        base_name = Path(self.baseFilename).name
        for log_file in self.log_dir.glob(f"{base_name}.*"):
            try:
                # Extract date from filename (e.g., proxy.log.2026-04-01)
                parts = log_file.name.split('.')
                if len(parts) >= 2:
                    date_part = parts[-1]
                    if len(date_part) == 10:  # YYYY-MM-DD format
                        file_date = datetime.strptime(date_part, '%Y-%m-%d')
                        if file_date < cutoff:
                            log_file.unlink()
                            logging.getLogger(__name__).debug(f"Removed old log file: {log_file}")
            except (ValueError, Exception) as e:
                # Skip files that don't match expected date pattern
                logging.getLogger(__name__).debug(f"Skipping log file {log_file}: {e}")


class LogManager:
    """
    Centralized log manager for the proxy.

    Manages two separate log files:
    1. Runtime log - proxy operation logs (startup, errors, etc.)
    2. Request log - Detailed request/response logging
    """

    def __init__(self, log_dir: str, retention_days: int = 7):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.retention_days = retention_days
        self.runtime_logger: Optional[logging.Logger] = None
        self.request_logger: Optional[logging.Logger] = None

        self._setup_runtime_logger()
        self._setup_request_logger()

    def _setup_runtime_logger(self):
        """Setup runtime log file handler."""
        self.runtime_logger = logging.getLogger('proxy.runtime')
        self.runtime_logger.setLevel(logging.INFO)

        # Remove any existing handlers
        self.runtime_logger.handlers.clear()

        # Create rotating file handler
        runtime_log_path = self.log_dir / "proxy.log"
        handler = RotatingFileHandler(
            str(runtime_log_path),
            retention_days=self.retention_days
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.runtime_logger.addHandler(handler)

        # Also add console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.runtime_logger.addHandler(console_handler)

        self.runtime_logger.propagate = False

    def _setup_request_logger(self):
        """Setup request detail log file handler."""
        self.request_logger = logging.getLogger('proxy.requests')
        self.request_logger.setLevel(logging.INFO)

        # Remove any existing handlers
        self.request_logger.handlers.clear()

        # Create rotating file handler
        request_log_path = self.log_dir / "requests.log"
        handler = RotatingFileHandler(
            str(request_log_path),
            retention_days=self.retention_days
        )
        # JSON format for request logs - single line per request
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.request_logger.addHandler(handler)

        self.request_logger.propagate = False

    def log_request(self, url: str, request_body: str, response_body: str,
                    extra_data: Optional[dict] = None):
        """
        Log a request with URL, body, and response.

        Args:
            url: Request URL
            request_body: Request body content
            response_body: Response body content
            extra_data: Optional additional data (tokens, cost, timing, etc.)
        """
        if not self.request_logger:
            return

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'url': url,
            'request_body': request_body,
            'response_body': response_body,
        }

        if extra_data:
            log_entry.update(extra_data)

        # Write as JSON line
        self.request_logger.info(json.dumps(log_entry, ensure_ascii=False))

    def log_info(self, message: str, *args):
        """Log runtime info message."""
        if self.runtime_logger:
            self.runtime_logger.info(message, *args)

    def log_error(self, message: str, *args):
        """Log runtime error message."""
        if self.runtime_logger:
            self.runtime_logger.error(message, *args)

    def log_warning(self, message: str, *args):
        """Log runtime warning message."""
        if self.runtime_logger:
            self.runtime_logger.warning(message, *args)

    def log_debug(self, message: str, *args):
        """Log runtime debug message."""
        if self.runtime_logger:
            self.runtime_logger.debug(message, *args)


# Global log manager instance (lazy initialized)
_log_manager: Optional[LogManager] = None


def get_log_manager() -> Optional[LogManager]:
    """Get the global log manager instance."""
    return _log_manager


def init_log_manager(log_dir: str = None, retention_days: int = 7) -> LogManager:
    """
    Initialize the global log manager.

    Args:
        log_dir: Directory for log files (default: data/logs)
        retention_days: Number of days to retain logs (default: 7)

    Returns:
        LogManager instance
    """
    global _log_manager

    if log_dir is None:
        from config.settings import BASE_DIR
        log_dir = str(BASE_DIR / "data" / "logs")

    _log_manager = LogManager(log_dir, retention_days)
    return _log_manager
