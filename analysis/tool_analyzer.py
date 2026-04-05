"""
Tool call analysis module.

Provides analysis of tool usage patterns, success rates, and performance metrics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
import json


@dataclass
class ToolStats:
    """Statistics for a single tool."""
    name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_duration_ms: int = 0
    avg_duration_ms: float = 0.0
    max_duration_ms: int = 0
    min_duration_ms: int = 0


@dataclass
class ToolSequence:
    """A sequence of tool calls."""
    tools: List[str]
    count: int = 0
    avg_duration_ms: float = 0.0


class ToolAnalyzer:
    """Analyzer for tool usage patterns."""

    # Tool categories
    TOOL_CATEGORIES = {
        "file_operations": ["Read", "Write", "Edit", "Glob", "Grep"],
        "execution": ["Bash", "Task"],
        "web": ["WebFetch", "WebSearch"],
        "planning": ["TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "EnterPlanMode", "ExitPlanMode"],
        "interaction": ["AskUserQuestion", "Skill"],
        "other": [],
    }

    def __init__(self, db):
        self.db = db

    def get_tool_usage_stats(self, hours: Optional[int] = None, models: Optional[List[str]] = None) -> List[ToolStats]:
        """Get usage statistics for all tools with optional time and model filter."""
        stats = self.db.get_tool_usage_stats_with_time_filter(hours=hours, models=models)

        result = []
        for stat in stats:
            result.append(ToolStats(
                name=stat.get("tool_name", "unknown"),
                total_calls=stat.get("count", 0),
                avg_duration_ms=stat.get("avg_duration_ms", 0),
            ))

        return result

    def get_tool_usage_distribution(self) -> Dict[str, int]:
        """Get the distribution of tool calls by tool name."""
        stats = self.get_tool_usage_stats()
        return {s.name: s.total_calls for s in stats}

    def get_tool_category_distribution(self) -> Dict[str, int]:
        """Get tool usage by category."""
        distribution = self.get_tool_usage_distribution()

        result = defaultdict(int)
        for tool, count in distribution.items():
            categorized = False
            for category, tools in self.TOOL_CATEGORIES.items():
                if tool in tools:
                    result[category] += count
                    categorized = True
                    break

            if not categorized:
                result["other"] += count

        return dict(result)

    def get_most_used_tools(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most frequently used tools."""
        stats = self.get_tool_usage_stats()
        sorted_stats = sorted(stats, key=lambda x: x.total_calls, reverse=True)

        return [
            {
                "name": s.name,
                "calls": s.total_calls,
                "avg_duration_ms": s.avg_duration_ms,
            }
            for s in sorted_stats[:limit]
        ]

    def get_slowest_tools(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the tools with longest average duration."""
        stats = self.get_tool_usage_stats()
        sorted_stats = sorted(
            [s for s in stats if s.avg_duration_ms > 0],
            key=lambda x: x.avg_duration_ms,
            reverse=True
        )

        return [
            {
                "name": s.name,
                "avg_duration_ms": s.avg_duration_ms,
                "calls": s.total_calls,
            }
            for s in sorted_stats[:limit]
        ]

    def get_tool_success_rate(self) -> Dict[str, float]:
        """Get success rate for each tool."""
        # This would require error tracking in tool_calls table
        # For now, return placeholder
        stats = self.get_tool_usage_stats()
        return {s.name: 100.0 for s in stats}  # Placeholder

    def get_tool_usage_over_time(self, days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """Get tool usage over time."""
        # This would need a custom query
        # Return placeholder for now
        return {}

    def analyze_tool_patterns(self) -> Dict[str, Any]:
        """Analyze tool usage patterns."""
        stats = self.get_tool_usage_stats()

        if not stats:
            return {
                "total_tools_used": 0,
                "total_calls": 0,
                "most_used": None,
                "slowest": None,
            }

        total_calls = sum(s.total_calls for s in stats)
        most_used = max(stats, key=lambda x: x.total_calls)
        slowest = max([s for s in stats if s.avg_duration_ms > 0],
                     key=lambda x: x.avg_duration_ms, default=None)

        return {
            "total_tools_used": len(stats),
            "total_calls": total_calls,
            "most_used": {
                "name": most_used.name,
                "calls": most_used.total_calls,
            } if most_used else None,
            "slowest": {
                "name": slowest.name,
                "avg_duration_ms": slowest.avg_duration_ms,
            } if slowest else None,
        }

    def get_tool_input_patterns(self, tool_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Analyze input patterns for a specific tool.

        Returns common input patterns and their frequencies.
        """
        # This would require analyzing tool_input_json from tool_calls
        # Placeholder for now
        return []


def format_tool_duration(duration_ms: int) -> str:
    """Format a duration for display."""
    if duration_ms >= 1000:
        return f"{duration_ms / 1000:.2f}s"
    else:
        return f"{duration_ms}ms"


def get_tool_description(tool_name: str) -> str:
    """Get a human-readable description for a tool."""
    descriptions = {
        "Read": "Read file contents",
        "Write": "Write or create files",
        "Edit": "Edit existing files",
        "Bash": "Execute shell commands",
        "Glob": "Find files by pattern",
        "Grep": "Search file contents",
        "WebFetch": "Fetch web content",
        "WebSearch": "Search the web",
        "Task": "Launch sub-agent tasks",
        "AskUserQuestion": "Ask user for input",
        "TaskCreate": "Create new task",
        "TaskUpdate": "Update task status",
        "TaskList": "List all tasks",
        "TaskGet": "Get task details",
        "EnterPlanMode": "Enter planning mode",
        "ExitPlanMode": "Exit planning mode",
        "Skill": "Execute a skill",
    }

    return descriptions.get(tool_name, "Unknown tool")