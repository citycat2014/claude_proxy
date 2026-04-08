"""
URL Filter Engine for request capture filtering.

Provides flexible URL matching with support for multiple filter types:
- domain: Substring match on domain
- path: Substring match on full URL path
- exact: Exact URL match
- wildcard: Glob pattern matching
- regex: Regular expression matching
"""

import re
import fnmatch
import logging
from typing import List, Optional
from datetime import datetime

from storage.database import Database
from storage.models import UrlFilter

logger = logging.getLogger(__name__)


class URLFilterEngine:
    """Engine for filtering URLs based on configurable rules."""

    def __init__(self, db: Database):
        self.db = db
        self._filters: List[UrlFilter] = []
        self._last_refresh = datetime.min
        self._refresh_interval = 60  # Refresh cache every 60 seconds
        self._load_filters()

    def _load_filters(self) -> None:
        """Load filters from database."""
        try:
            self._filters = self.db.get_url_filters(enabled_only=True)
            self._last_refresh = datetime.now()
            logger.info(f"Loaded {len(self._filters)} URL filters")
        except Exception as e:
            logger.error(f"Failed to load URL filters: {e}")
            self._filters = []

    def _should_refresh(self) -> bool:
        """Check if filters need refresh."""
        return (datetime.now() - self._last_refresh).seconds > self._refresh_interval

    def refresh_filters(self) -> None:
        """Force refresh filters from database."""
        self._load_filters()

    def should_capture(self, url: str) -> bool:
        """
        Check if URL should be captured based on filter rules.

        Rules are evaluated in priority order. First matching rule wins.
        If no rules match, returns False (default deny).

        Args:
            url: Full URL to check

        Returns:
            True if URL should be captured, False otherwise
        """
        if self._should_refresh():
            self._load_filters()

        if not self._filters:
            # No filters configured - use default behavior (capture messages API)
            return "/messages" in url or "/v1/messages" in url

        # Sort by priority (lower number = higher priority)
        sorted_filters = sorted(self._filters, key=lambda f: f.priority)

        for filter_rule in sorted_filters:
            if self._matches(url, filter_rule):
                result = filter_rule.action == 'include'
                logger.debug(f"URL {url} matched filter '{filter_rule.name}' ({filter_rule.action}): {result}")
                return result

        # No matching filter - deny by default
        logger.debug(f"URL {url} did not match any filter, denying")
        return False

    def _matches(self, url: str, filter_rule: UrlFilter) -> bool:
        """Check if URL matches a filter rule."""
        pattern = filter_rule.pattern
        filter_type = filter_rule.filter_type

        try:
            if filter_type == 'domain':
                return pattern.lower() in url.lower()

            elif filter_type == 'path':
                return pattern in url

            elif filter_type == 'exact':
                return url == pattern

            elif filter_type == 'wildcard':
                return fnmatch.fnmatch(url, pattern)

            elif filter_type == 'regex':
                return bool(re.search(pattern, url))

            else:
                logger.warning(f"Unknown filter type: {filter_type}")
                return False

        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return False
        except Exception as e:
            logger.error(f"Error matching URL {url} with filter {filter_rule.name}: {e}")
            return False

    def get_filter_stats(self) -> dict:
        """Get statistics about configured filters."""
        all_filters = self.db.get_url_filters(enabled_only=False)

        return {
            "total": len(all_filters),
            "enabled": sum(1 for f in all_filters if f.is_enabled),
            "disabled": sum(1 for f in all_filters if not f.is_enabled),
            "include_rules": sum(1 for f in all_filters if f.action == 'include'),
            "exclude_rules": sum(1 for f in all_filters if f.action == 'exclude'),
            "by_type": {
                "domain": sum(1 for f in all_filters if f.filter_type == 'domain'),
                "path": sum(1 for f in all_filters if f.filter_type == 'path'),
                "exact": sum(1 for f in all_filters if f.filter_type == 'exact'),
                "wildcard": sum(1 for f in all_filters if f.filter_type == 'wildcard'),
                "regex": sum(1 for f in all_filters if f.filter_type == 'regex'),
            }
        }

    def test_pattern(self, pattern: str, filter_type: str, test_url: str) -> bool:
        """Test if a pattern matches a URL without saving."""
        try:
            if filter_type == 'domain':
                return pattern.lower() in test_url.lower()
            elif filter_type == 'path':
                return pattern in test_url
            elif filter_type == 'exact':
                return test_url == pattern
            elif filter_type == 'wildcard':
                return fnmatch.fnmatch(test_url, pattern)
            elif filter_type == 'regex':
                return bool(re.search(pattern, test_url))
            return False
        except Exception as e:
            logger.error(f"Error testing pattern: {e}")
            return False
