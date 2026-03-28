"""
Token usage analysis and cost calculation.

Provides functions for analyzing token usage patterns and calculating costs.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from config.settings import PRICING


@dataclass
class TokenUsage:
    """Token usage summary."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0


@dataclass
class TokenBreakdown:
    """Token usage breakdown by category."""
    by_model: Dict[str, TokenUsage]
    by_day: Dict[str, TokenUsage]
    by_session: Dict[str, TokenUsage]


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """
    Calculate the cost for a given token usage.

    Args:
        model: The model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_creation_tokens: Number of cache creation tokens
        cache_read_tokens: Number of cache read tokens

    Returns:
        Cost in USD
    """
    pricing = PRICING.get(model, PRICING.get("default", {}))

    input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0)
    output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0)
    cache_write_cost = (cache_creation_tokens / 1_000_000) * pricing.get("cache_write", 0)
    cache_read_cost = (cache_read_tokens / 1_000_000) * pricing.get("cache_read", 0)

    return input_cost + output_cost + cache_write_cost + cache_read_cost


def format_token_count(count: int) -> str:
    """Format a token count for display."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.2f}M"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K"
    else:
        return str(count)


def format_cost(cost: float) -> str:
    """Format a cost for display."""
    if cost >= 1.0:
        return f"${cost:.2f}"
    elif cost >= 0.01:
        return f"${cost:.3f}"
    else:
        return f"${cost:.4f}"


class TokenAnalyzer:
    """Analyzer for token usage patterns."""

    def __init__(self, db):
        self.db = db

    def get_overall_usage(self) -> TokenUsage:
        """Get overall token usage."""
        stats = self.db.get_summary_stats()

        return TokenUsage(
            input_tokens=stats.get("total_input_tokens", 0),
            output_tokens=stats.get("total_output_tokens", 0),
            total_tokens=stats.get("total_input_tokens", 0) + stats.get("total_output_tokens", 0),
            cost=stats.get("total_cost", 0),
        )

    def get_usage_by_model(self) -> Dict[str, TokenUsage]:
        """Get token usage breakdown by model."""
        result = {}

        model_stats = self.db.get_model_usage_stats()
        for stat in model_stats:
            model = stat.get("model", "unknown")
            result[model] = TokenUsage(
                input_tokens=stat.get("total_input_tokens", 0),
                output_tokens=stat.get("total_output_tokens", 0),
                total_tokens=stat.get("total_input_tokens", 0) + stat.get("total_output_tokens", 0),
                cost=stat.get("total_cost", 0),
            )

        return result

    def get_usage_timeline(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily token usage for the past N days."""
        return self.db.get_timeline_stats(days)

    def estimate_monthly_cost(self) -> float:
        """Estimate monthly cost based on current usage."""
        timeline = self.get_usage_timeline(days=7)

        if not timeline:
            return 0.0

        # Calculate average daily cost
        total_cost = sum(day.get("cost", 0) for day in timeline)
        days_with_usage = len([d for d in timeline if d.get("requests", 0) > 0])

        if days_with_usage == 0:
            return 0.0

        avg_daily_cost = total_cost / days_with_usage

        # Estimate monthly
        return avg_daily_cost * 30

    def get_efficiency_metrics(self) -> Dict[str, Any]:
        """Get efficiency metrics."""
        stats = self.db.get_summary_stats()

        total_input = stats.get("total_input_tokens", 0)
        total_output = stats.get("total_output_tokens", 0)

        # Input/output ratio
        io_ratio = total_input / total_output if total_output > 0 else 0

        # Average tokens per request
        total_requests = stats.get("total_requests", 0)
        avg_tokens_per_request = (total_input + total_output) / total_requests if total_requests > 0 else 0

        # Cache efficiency
        # Note: cache_read_tokens means we saved on input tokens
        cache_read = stats.get("cache_read_tokens", 0)
        cache_efficiency = cache_read / total_input if total_input > 0 else 0

        return {
            "input_output_ratio": io_ratio,
            "avg_tokens_per_request": avg_tokens_per_request,
            "cache_efficiency": cache_efficiency,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_requests": total_requests,
        }