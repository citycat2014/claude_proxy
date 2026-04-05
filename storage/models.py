"""
SQLAlchemy ORM models for pkts_capture.

Defines database schema using SQLAlchemy declarative base.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Index, Text
)
from sqlalchemy.orm import declarative_base, relationship, Session as DBSession
from sqlalchemy.sql import func

from config.settings import DATABASE_PATH

Base = declarative_base()


class Session(Base):
    """A Claude Code session."""
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    model = Column(String(100), nullable=True)
    user_agent = Column(String(255), nullable=True)
    working_directory = Column(String(500), nullable=True)

    # Relationships
    requests = relationship("Request", back_populates="session", lazy="dynamic")

    __table_args__ = (
        Index('idx_sessions_started', 'started_at'),
    )

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


class Request(Base):
    """A single API request/response."""
    __tablename__ = 'requests'

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(255), unique=True, nullable=False, index=True)
    session_id = Column(String(255), ForeignKey('sessions.session_id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    method = Column(String(20), nullable=True)
    endpoint = Column(String(500), nullable=True)

    # Request info
    model = Column(String(100), nullable=True)
    system_prompt = Column(Text, nullable=True)
    messages_json = Column(Text, nullable=True)

    # Response info
    response_status = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    is_streaming = Column(Boolean, default=False)

    # Token usage
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cache_creation_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)

    # Cost
    cost = Column(Float, default=0.0)

    # Raw data
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)

    # Parsed response content
    response_text = Column(Text, nullable=True)
    response_thinking = Column(Text, nullable=True)

    # Phase timings (in milliseconds)
    dns_ms = Column(Integer, nullable=True)           # DNS lookup time
    connect_ms = Column(Integer, nullable=True)       # TCP connection time
    tls_ms = Column(Integer, nullable=True)           # TLS handshake time
    send_ms = Column(Integer, nullable=True)          # Request send time
    wait_ms = Column(Integer, nullable=True)          # Server processing time (TTFB)
    receive_ms = Column(Integer, nullable=True)       # Response receive time

    # Streaming-specific timings
    time_to_first_token_ms = Column(Integer, nullable=True)   # Time to first token
    time_to_last_token_ms = Column(Integer, nullable=True)    # Time to last token
    avg_token_latency_ms = Column(Integer, nullable=True)     # Average inter-token latency

    # Relationships
    session = relationship("Session", back_populates="requests")
    tool_calls = relationship("ToolCall", back_populates="request", lazy="dynamic")
    messages = relationship("Message", back_populates="request", lazy="dynamic")

    __table_args__ = (
        Index('idx_requests_session', 'session_id'),
        Index('idx_requests_timestamp', 'timestamp'),
        Index('idx_requests_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_requests_model_timestamp', 'model', 'timestamp'),
    )

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
            "dns_ms": self.dns_ms,
            "connect_ms": self.connect_ms,
            "tls_ms": self.tls_ms,
            "send_ms": self.send_ms,
            "wait_ms": self.wait_ms,
            "receive_ms": self.receive_ms,
            "time_to_first_token_ms": self.time_to_first_token_ms,
            "time_to_last_token_ms": self.time_to_last_token_ms,
            "avg_token_latency_ms": self.avg_token_latency_ms,
        }


class ToolCall(Base):
    """A tool use event."""
    __tablename__ = 'tool_calls'

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(255), ForeignKey('requests.request_id'), nullable=False)
    tool_name = Column(String(100), nullable=False, index=True)
    tool_input_json = Column(Text, nullable=True)
    tool_result = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    duration_ms = Column(Integer, nullable=True)

    # Relationships
    request = relationship("Request", back_populates="tool_calls")

    __table_args__ = (
        Index('idx_tool_calls_request', 'request_id'),
        Index('idx_tool_calls_name', 'tool_name'),
    )

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
            "tool_result": self.tool_result[:500] if self.tool_result else "",
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration_ms": self.duration_ms,
        }


class Message(Base):
    """A message in a conversation."""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(255), ForeignKey('requests.request_id'), nullable=False)
    role = Column(String(50), nullable=False)  # user/assistant
    content_type = Column(String(50), nullable=True)  # text/tool_use/tool_result
    content_text = Column(Text, nullable=True)
    sequence = Column(Integer, default=0)

    # Relationships
    request = relationship("Request", back_populates="messages")

    __table_args__ = (
        Index('idx_messages_request', 'request_id'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "role": self.role,
            "content_type": self.content_type,
            "content_text": self.content_text,
            "sequence": self.sequence,
        }


class Statistics(Base):
    """Statistics snapshot."""
    __tablename__ = 'statistics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    period_type = Column(String(20), nullable=True)  # hour/day
    period_start = Column(DateTime, nullable=True)
    request_count = Column(Integer, default=0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    avg_response_time_ms = Column(Float, nullable=True)

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


class UrlFilter(Base):
    """URL filter rule for capturing requests."""
    __tablename__ = 'url_filters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    pattern = Column(String(500), nullable=False)
    filter_type = Column(String(20), default='domain')  # domain, path, regex, exact, wildcard
    action = Column(String(10), default='include')  # include, exclude
    priority = Column(Integer, default=100)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_url_filters_enabled', 'is_enabled'),
        Index('idx_url_filters_priority', 'priority'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pattern": self.pattern,
            "filter_type": self.filter_type,
            "action": self.action,
            "priority": self.priority,
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SystemReminder(Base):
    """Deduplicated system-reminder content."""
    __tablename__ = 'system_reminders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)
    first_seen_at = Column(DateTime, default=datetime.now)
    use_count = Column(Integer, default=1)

    __table_args__ = (
        Index('idx_system_reminders_hash', 'content_hash'),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content_hash": self.content_hash,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "use_count": self.use_count,
        }


# Create engine
engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)

# Create all tables
Base.metadata.create_all(engine)
