"""
Data models for pkts_capture.

Defines the schema and data structures for storing captured interactions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


@dataclass
class Session:
    """A Claude Code session."""
    id: Optional[int] = None
    session_id: str = ""
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    model: str = ""
    user_agent: str = ""
    working_directory: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "model": self.model,
            "user_agent": self.user_agent,
            "working_directory": self.working_directory,
        }


@dataclass
class Request:
    """A single API request/response."""
    id: Optional[int] = None
    request_id: str = ""
    session_id: str = ""
    timestamp: Optional[datetime] = None
    method: str = ""
    endpoint: str = ""

    # Request info
    model: str = ""
    system_prompt: str = ""
    messages_json: str = ""

    # Response info
    response_status: int = 0
    response_time_ms: int = 0
    is_streaming: bool = False

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    # Cost
    cost: float = 0.0

    # Raw data
    request_body: str = ""
    response_body: str = ""

    # Parsed response content
    response_text: str = ""  # 整合后的文本响应
    response_thinking: str = ""  # 整合后的思考过程

    def get_messages(self) -> List[Dict[str, Any]]:
        """Parse messages from JSON."""
        if not self.messages_json:
            return []
        try:
            return json.loads(self.messages_json)
        except json.JSONDecodeError:
            return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "method": self.method,
            "endpoint": self.endpoint,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "messages_json": self.messages_json,
            "response_status": self.response_status,
            "response_time_ms": self.response_time_ms,
            "is_streaming": self.is_streaming,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cost": self.cost,
            "request_body": self.request_body,
            "response_body": self.response_body,
            "response_text": self.response_text,
            "response_thinking": self.response_thinking,
        }


@dataclass
class ToolCall:
    """A tool use event."""
    id: Optional[int] = None
    request_id: str = ""
    tool_name: str = ""
    tool_input_json: str = ""
    tool_result: str = ""
    timestamp: Optional[datetime] = None
    duration_ms: int = 0

    def get_input(self) -> Dict[str, Any]:
        """Parse tool input from JSON."""
        if not self.tool_input_json:
            return {}
        try:
            return json.loads(self.tool_input_json)
        except json.JSONDecodeError:
            return {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "tool_input": self.get_input(),
            "tool_result": self.tool_result[:500] if self.tool_result else "",  # Truncate for display
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration_ms": self.duration_ms,
        }


@dataclass
class Message:
    """A message in a conversation."""
    id: Optional[int] = None
    request_id: str = ""
    role: str = ""  # user/assistant
    content_type: str = ""  # text/tool_use/tool_result
    content_text: str = ""
    sequence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "role": self.role,
            "content_type": self.content_type,
            "content_text": self.content_text,
            "sequence": self.sequence,
        }


@dataclass
class Statistics:
    """Statistics snapshot."""
    id: Optional[int] = None
    period_type: str = ""  # hour/day
    period_start: Optional[datetime] = None
    request_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    avg_response_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "period_type": self.period_type,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "request_count": self.request_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "avg_response_time_ms": self.avg_response_time_ms,
        }