"""
Statistics and reporting module.

Provides high-level statistics and report generation.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class SummaryStats:
    """Overall summary statistics."""
    total_requests: int = 0
    total_sessions: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    avg_response_time_ms: float = 0.0
    requests_today: int = 0
    cost_today: float = 0.0


class StatisticsEngine:
    """Engine for computing statistics."""

    def __init__(self, db):
        self.db = db

    def get_summary(self, hours: Optional[int] = None) -> SummaryStats:
        """Get overall summary statistics with optional time filter."""
        stats = self.db.get_summary_stats_with_time_filter(hours)
        today_stats = self.db.get_today_stats()

        return SummaryStats(
            total_requests=stats.get("total_requests", 0),
            total_sessions=stats.get("total_sessions", 0),
            total_input_tokens=stats.get("total_input_tokens", 0),
            total_output_tokens=stats.get("total_output_tokens", 0),
            total_cost=stats.get("total_cost", 0),
            avg_response_time_ms=stats.get("avg_response_time_ms", 0),
            requests_today=today_stats.get("requests", 0),
            cost_today=today_stats.get("cost", 0),
        )

    def get_request_volume_timeline(self, hours: Optional[float] = None, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get request volume over time with optional filter."""
        if hours and hours <= 1:
            # Use minute-level grouping for very short time ranges (< 1 hour)
            minutes = int(hours * 60)
            return self.db.get_timeline_stats_minute(minutes)
        elif hours and hours <= 24:
            # Use hourly grouping for short time ranges
            return self.db.get_timeline_stats_hourly(int(hours))
        elif days:
            return self.db.get_timeline_stats(days)
        else:
            return self.db.get_timeline_stats(7)

    def get_cost_timeline(self, hours: Optional[int] = None, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get cost over time with optional filter."""
        if hours and hours <= 24:
            timeline = self.db.get_timeline_stats_hourly(hours)
        elif days:
            timeline = self.db.get_timeline_stats(days)
        else:
            timeline = self.db.get_timeline_stats(7)

        return [
            {
                "date": t.get("date") or t.get("hour"),
                "cost": t.get("cost", 0),
                "requests": t.get("requests", 0),
            }
            for t in timeline
        ]

    def get_model_distribution(self, hours: Optional[int] = None) -> Dict[str, int]:
        """Get distribution of requests by model with optional time filter."""
        stats = self.db.get_model_usage_stats_with_time_filter(hours)

        return {
            s.get("model", "unknown"): s.get("count", 0)
            for s in stats
        }

    def get_hourly_distribution(self) -> Dict[int, int]:
        """Get distribution of requests by hour of day."""
        # This would need a custom query
        # Placeholder
        return {i: 0 for i in range(24)}

    def get_response_time_stats(self) -> Dict[str, float]:
        """Get response time statistics."""
        stats = self.db.get_summary_stats()

        return {
            "avg_ms": stats.get("avg_response_time_ms", 0),
            "min_ms": 0,  # Would need separate query
            "max_ms": 0,  # Would need separate query
        }

    def get_session_stats(self) -> Dict[str, Any]:
        """Get session-related statistics."""
        return {
            "total_sessions": self.db.get_session_count(),
            "avg_requests_per_session": self.db.get_avg_requests_per_session(),
            "avg_tokens_per_session": self.db.get_avg_tokens_per_session(),
        }

    def generate_report(self, period: str = "week") -> Dict[str, Any]:
        """
        Generate a comprehensive report.

        Args:
            period: "day", "week", or "month"

        Returns:
            Report dictionary
        """
        days_map = {"day": 1, "week": 7, "month": 30}
        days = days_map.get(period, 7)

        summary = self.get_summary()
        timeline = self.get_request_volume_timeline(days=days)

        return {
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_requests": summary.total_requests,
                "total_sessions": summary.total_sessions,
                "total_tokens": summary.total_input_tokens + summary.total_output_tokens,
                "total_cost": summary.total_cost,
                "input_tokens": summary.total_input_tokens,
                "output_tokens": summary.total_output_tokens,
            },
            "timeline": timeline,
            "averages": {
                "avg_response_time_ms": summary.avg_response_time_ms,
                "avg_tokens_per_request": (summary.total_input_tokens + summary.total_output_tokens) / summary.total_requests if summary.total_requests > 0 else 0,
                "avg_cost_per_request": summary.total_cost / summary.total_requests if summary.total_requests > 0 else 0,
            },
            "model_distribution": self.get_model_distribution(),
        }


def format_percentage(value: float, total: float) -> str:
    """Format a percentage value."""
    if total == 0:
        return "0%"
    return f"{(value / total) * 100:.1f}%"


def format_number(value: int) -> str:
    """Format a number for display."""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return str(value)