"""
Database operations using SQLAlchemy ORM.

Provides CRUD operations and queries using ORM instead of raw SQL.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session as DBSession, sessionmaker, joinedload

from storage.models import (
    engine, Session, Request, ToolCall, Message, Statistics
)

# Create session factory
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)


class Database:
    """SQLAlchemy ORM database handler."""

    def __init__(self, db_path: str = None):
        """Initialize database (db_path is kept for compatibility)."""
        self.session_factory = SessionFactory

    def get_db_session(self) -> DBSession:
        """Get a new database session."""
        return self.session_factory()

    # ============ Session operations ============

    def upsert_session(self, session: Session) -> Session:
        """Insert or update a session."""
        db = self.get_db_session()
        try:
            # Check if session exists
            existing = db.query(Session).filter_by(session_id=session.session_id).first()

            if existing:
                # Update existing session
                existing.ended_at = session.ended_at
                existing.total_requests = session.total_requests
                existing.total_input_tokens = session.total_input_tokens
                existing.total_output_tokens = session.total_output_tokens
                existing.total_cost = session.total_cost
                existing.model = session.model
                session.id = existing.id
            else:
                # Insert new session
                db.add(session)
                db.flush()  # Get the ID

            db.commit()
            return session
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        db = self.session_factory()
        try:
            return db.query(Session).filter_by(session_id=session_id).first()
        finally:
            db.close()

    def get_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        session_id_filter: str = None,
        model_filter: str = None,
        date_from: str = None,
        date_to: str = None,
        request_id_filter: str = None
    ) -> tuple[List[Session], int]:
        """Get sessions list with filtering."""
        db = self.session_factory()
        try:
            query = db.query(Session)

            # Apply filters
            if session_id_filter:
                query = query.filter(Session.session_id.contains(session_id_filter))
            if request_id_filter:
                # Join with requests table to filter by request_id
                query = query.join(Request, Session.session_id == Request.session_id)
                query = query.filter(Request.request_id.contains(request_id_filter))
            if model_filter:
                query = query.filter(Session.model == model_filter)
            if date_from:
                query = query.filter(Session.started_at >= date_from)
            if date_to:
                query = query.filter(Session.started_at <= date_to)

            # Get total count
            total = query.count()

            # Apply pagination and ordering - use ended_at if available, otherwise started_at
            sessions = query.order_by(desc(func.coalesce(Session.ended_at, Session.started_at))).offset(offset).limit(limit).all()

            return sessions, total
        finally:
            db.close()

    # ============ Request operations ============

    def save_request(self, request: Request) -> Request:
        """Save a request."""
        db = self.session_factory()
        try:
            db.add(request)
            db.commit()
            return request
        finally:
            db.close()

    def get_request(self, request_id: str) -> Optional[Request]:
        """Get a request by ID."""
        db = self.session_factory()
        try:
            return db.query(Request).filter_by(request_id=request_id).first()
        finally:
            db.close()

    def get_requests_by_session(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Request]:
        """Get requests for a session."""
        db = self.session_factory()
        try:
            return db.query(Request)\
                .filter_by(session_id=session_id)\
                .order_by(desc(Request.timestamp))\
                .offset(offset)\
                .limit(limit)\
                .all()
        finally:
            db.close()

    def get_request_count_by_session(self, session_id: str) -> int:
        """Count requests for a session."""
        db = self.session_factory()
        try:
            return db.query(Request).filter_by(session_id=session_id).count()
        finally:
            db.close()

    # ============ Tool call operations ============

    def save_tool_call(self, tool_call: ToolCall) -> ToolCall:
        """Save a tool call."""
        db = self.session_factory()
        try:
            db.add(tool_call)
            db.commit()
            return tool_call
        finally:
            db.close()

    def get_tool_calls_by_request(self, request_id: str) -> List[Dict[str, Any]]:
        """Get tool calls for a request."""
        db = self.session_factory()
        try:
            tool_calls = db.query(ToolCall).filter_by(request_id=request_id).all()
            return [tc.to_dict() for tc in tool_calls]
        finally:
            db.close()

    # ============ Statistics operations ============

    def get_summary_stats(self, hours: int = None) -> Dict[str, Any]:
        """Get overall statistics summary (alias for get_statistics_summary)."""
        return self.get_statistics_summary(hours)

    def get_statistics_summary(self, hours: int = None) -> Dict[str, Any]:
        """Get overall statistics summary."""
        db = self.session_factory()
        try:
            query = db.query(
                func.count(Request.id).label('total_requests'),
                func.sum(Request.input_tokens).label('total_input_tokens'),
                func.sum(Request.output_tokens).label('total_output_tokens'),
                func.sum(Request.cost).label('total_cost'),
                func.avg(Request.response_time_ms).label('avg_response_time_ms')
            )

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(Request.timestamp >= since)

            result = query.first()

            # Get session count
            session_query = db.query(func.count(Session.id))
            if hours:
                since = datetime.now() - timedelta(hours=hours)
                session_query = session_query.filter(Session.started_at >= since)
            session_count = session_query.scalar()

            return {
                "total_requests": result.total_requests or 0,
                "total_sessions": session_count or 0,
                "total_input_tokens": result.total_input_tokens or 0,
                "total_output_tokens": result.total_output_tokens or 0,
                "total_cost": result.total_cost or 0.0,
                "avg_response_time_ms": result.avg_response_time_ms or 0.0,
            }
        finally:
            db.close()

    def get_summary_stats_with_time_filter(self, hours: int = None) -> Dict[str, Any]:
        """Get summary stats with optional time filter."""
        return self.get_statistics_summary(hours)

    def get_today_stats(self) -> Dict[str, Any]:
        """Get today's statistics."""
        db = self.session_factory()
        try:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            result = db.query(
                func.count(Request.id).label('requests'),
                func.sum(Request.cost).label('cost')
            ).filter(Request.timestamp >= today).first()

            return {
                "requests": result.requests or 0,
                "cost": result.cost or 0.0
            }
        finally:
            db.close()

    def get_timeline_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get request volume by day."""
        db = self.session_factory()
        try:
            since = datetime.now() - timedelta(days=days)

            results = db.query(
                func.date(Request.timestamp).label('date'),
                func.count(Request.id).label('count')
            ).filter(Request.timestamp >= since)\
                .group_by(func.date(Request.timestamp))\
                .order_by(func.date(Request.timestamp))\
                .all()

            return [{"date": str(r.date), "count": r.count} for r in results]
        finally:
            db.close()

    def get_timeline_stats_hourly(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get request volume by hour."""
        db = self.session_factory()
        try:
            since = datetime.now() - timedelta(hours=hours)

            results = db.query(
                func.strftime('%Y-%m-%dT%H:00:00', Request.timestamp).label('timestamp'),
                func.count(Request.id).label('count')
            ).filter(Request.timestamp >= since)\
                .group_by(func.strftime('%Y-%m-%dT%H:00:00', Request.timestamp))\
                .order_by(func.strftime('%Y-%m-%dT%H:00:00', Request.timestamp))\
                .all()

            return [{"timestamp": r.timestamp, "count": r.count} for r in results]
        finally:
            db.close()

    def get_timeline_stats_minute(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get request volume by minute."""
        db = self.session_factory()
        try:
            since = datetime.now() - timedelta(minutes=minutes)

            results = db.query(
                func.strftime('%Y-%m-%dT%H:%M:00', Request.timestamp).label('timestamp'),
                func.count(Request.id).label('count')
            ).filter(Request.timestamp >= since)\
                .group_by(func.strftime('%Y-%m-%dT%H:%M:00', Request.timestamp))\
                .order_by(func.strftime('%Y-%m-%dT%H:%M:00', Request.timestamp))\
                .all()

            return [{"timestamp": r.timestamp, "count": r.count} for r in results]
        finally:
            db.close()

    def get_model_distribution(self, hours: int = None) -> Dict[str, Dict[str, Any]]:
        """Get model usage distribution."""
        db = self.session_factory()
        try:
            query = db.query(
                Request.model,
                func.count(Request.id).label('requests'),
                func.sum(Request.input_tokens + Request.output_tokens).label('tokens'),
                func.sum(Request.cost).label('cost')
            ).filter(Request.model.isnot(None))

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(Request.timestamp >= since)

            results = query.group_by(Request.model).all()

            return {
                r.model: {
                    "requests": r.requests,
                    "tokens": r.tokens or 0,
                    "cost": r.cost or 0.0
                }
                for r in results
            }
        finally:
            db.close()

    def get_usage_by_model(self) -> List[Dict[str, Any]]:
        """Get token usage by model."""
        db = self.session_factory()
        try:
            results = db.query(
                Request.model,
                func.sum(Request.input_tokens).label('input_tokens'),
                func.sum(Request.output_tokens).label('output_tokens'),
                func.sum(Request.cost).label('cost')
            ).filter(Request.model.isnot(None))\
                .group_by(Request.model).all()

            return [
                {
                    "model": r.model,
                    "input_tokens": r.input_tokens or 0,
                    "output_tokens": r.output_tokens or 0,
                    "cost": r.cost or 0.0
                }
                for r in results
            ]
        finally:
            db.close()

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        db = self.session_factory()
        try:
            result = db.query(
                func.sum(Request.cache_read_tokens).label('tokens_from_cache'),
                func.count(Request.id).filter(Request.cache_read_tokens > 0).label('cache_hits'),
                func.count(Request.id).filter(Request.cache_read_tokens == 0).label('cache_misses')
            ).first()

            return {
                "tokens_from_cache": result.tokens_from_cache or 0,
                "cache_hits": result.cache_hits or 0,
                "cache_misses": result.cache_misses or 0
            }
        finally:
            db.close()

    def get_daily_costs(self) -> List[Dict[str, Any]]:
        """Get daily cost aggregation."""
        db = self.session_factory()
        try:
            results = db.query(
                func.date(Request.timestamp).label('date'),
                func.sum(Request.cost).label('cost')
            ).group_by(func.date(Request.timestamp))\
                .order_by(desc(func.date(Request.timestamp)))\
                .limit(30).all()

            return [{"date": str(r.date), "cost": r.cost or 0.0} for r in results]
        finally:
            db.close()

    def get_requests(self, limit: int = 1000) -> List[Request]:
        """Get requests list."""
        db = self.session_factory()
        try:
            return db.query(Request).order_by(desc(Request.timestamp)).limit(limit).all()
        finally:
            db.close()

    # ============ Tool usage operations ============

    def get_tool_usage_stats(self, hours: int = None) -> List[Any]:
        """Get tool usage statistics."""
        db = self.session_factory()
        try:
            query = db.query(
                ToolCall.tool_name,
                func.count(ToolCall.id).label('total_calls'),
                func.avg(ToolCall.duration_ms).label('avg_duration_ms'),
                func.sum(ToolCall.duration_ms).label('total_duration_ms')
            )

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(ToolCall.timestamp >= since)

            results = query.group_by(ToolCall.tool_name)\
                .order_by(desc('total_calls')).all()

            # Return named tuples that have attributes
            return results
        finally:
            db.close()

    def get_tool_usage_by_hour(self) -> List[Dict[str, Any]]:
        """Get tool usage by hour."""
        db = self.session_factory()
        try:
            results = db.query(
                func.strftime('%H', ToolCall.timestamp).label('hour'),
                func.count(ToolCall.id).label('count')
            ).group_by(func.strftime('%H', ToolCall.timestamp)).all()

            return [{"hour": int(r.hour), "count": r.count} for r in results]
        finally:
            db.close()

    # ============ Analysis module compatibility ============

    def get_tool_usage_stats_with_time_filter(self, hours: int = None) -> List[Dict[str, Any]]:
        """Get tool usage stats with optional time filter (for ToolAnalyzer)."""
        db = self.session_factory()
        try:
            query = db.query(
                ToolCall.tool_name,
                func.count(ToolCall.id).label('count'),
                func.avg(ToolCall.duration_ms).label('avg_duration_ms')
            )

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(ToolCall.timestamp >= since)

            results = query.group_by(ToolCall.tool_name).all()

            return [
                {
                    "tool_name": r.tool_name,
                    "count": r.count,
                    "avg_duration_ms": r.avg_duration_ms or 0
                }
                for r in results
            ]
        finally:
            db.close()

    def get_model_usage_stats_with_time_filter(self, hours: int = None) -> List[Dict[str, Any]]:
        """Get model usage stats with optional time filter (for StatisticsEngine)."""
        db = self.session_factory()
        try:
            query = db.query(
                Request.model,
                func.count(Request.id).label('count')
            ).filter(Request.model.isnot(None))

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(Request.timestamp >= since)

            results = query.group_by(Request.model).all()

            return [
                {"model": r.model, "count": r.count}
                for r in results
            ]
        finally:
            db.close()

    def get_model_usage_stats(self) -> List[Dict[str, Any]]:
        """Get model usage stats (for TokenAnalyzer)."""
        db = self.session_factory()
        try:
            results = db.query(
                Request.model,
                func.sum(Request.input_tokens).label('total_input_tokens'),
                func.sum(Request.output_tokens).label('total_output_tokens'),
                func.sum(Request.cost).label('total_cost')
            ).filter(Request.model.isnot(None))\
                .group_by(Request.model).all()

            return [
                {
                    "model": r.model,
                    "total_input_tokens": r.total_input_tokens or 0,
                    "total_output_tokens": r.total_output_tokens or 0,
                    "total_cost": r.total_cost or 0.0
                }
                for r in results
            ]
        finally:
            db.close()

    def get_session_count(self) -> int:
        """Get total session count (for StatisticsEngine)."""
        db = self.session_factory()
        try:
            return db.query(func.count(Session.id)).scalar() or 0
        finally:
            db.close()

    def get_avg_requests_per_session(self) -> float:
        """Get average requests per session (for StatisticsEngine)."""
        db = self.session_factory()
        try:
            total_requests = db.query(func.count(Request.id)).scalar() or 0
            total_sessions = db.query(func.count(Session.id)).scalar() or 0
            if total_sessions == 0:
                return 0.0
            return total_requests / total_sessions
        finally:
            db.close()

    def get_avg_tokens_per_session(self) -> float:
        """Get average tokens per session (for StatisticsEngine)."""
        db = self.session_factory()
        try:
            total_input = db.query(func.sum(Request.input_tokens)).scalar() or 0
            total_output = db.query(func.sum(Request.output_tokens)).scalar() or 0
            total_sessions = db.query(func.count(Session.id)).scalar() or 0
            if total_sessions == 0:
                return 0.0
            return (total_input + total_output) / total_sessions
        finally:
            db.close()
