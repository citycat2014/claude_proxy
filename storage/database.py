"""
Database operations using SQLAlchemy ORM.

Provides CRUD operations and queries using ORM instead of raw SQL.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session as DBSession, sessionmaker, joinedload

from storage.models import (
    engine, Session, Request, ToolCall, Message, Statistics, SystemReminder, UrlFilter
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

    @contextmanager
    def db_session(self):
        """Context manager for database sessions."""
        db = self.session_factory()
        try:
            yield db
        finally:
            db.close()

    # ============ Session operations ============

    def upsert_session(self, session: Session) -> Session:
        """Insert or update a session."""
        with self.db_session() as db:
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

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        with self.db_session() as db:
            return db.query(Session).filter_by(session_id=session_id).first()

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
        """Get sessions list with filtering, ordered by most recent request time."""
        with self.db_session() as db:
            # Subquery to get latest request timestamp for each session
            latest_request_subq = db.query(
                Request.session_id,
                func.max(Request.timestamp).label('latest_request_time')
            ).group_by(Request.session_id).subquery()

            # Main query with outer join to include sessions even without requests
            query = db.query(Session, latest_request_subq.c.latest_request_time)
            query = query.outerjoin(
                latest_request_subq,
                Session.session_id == latest_request_subq.c.session_id
            )

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

            # Get total count (need to handle the join properly for count)
            count_query = db.query(func.count(func.distinct(Session.id)))
            if session_id_filter:
                count_query = count_query.filter(Session.session_id.contains(session_id_filter))
            if request_id_filter:
                count_query = count_query.join(Request, Session.session_id == Request.session_id)
                count_query = count_query.filter(Request.request_id.contains(request_id_filter))
            if model_filter:
                count_query = count_query.filter(Session.model == model_filter)
            if date_from:
                count_query = count_query.filter(Session.started_at >= date_from)
            if date_to:
                count_query = count_query.filter(Session.started_at <= date_to)
            total = count_query.scalar()

            # Apply pagination and ordering - by latest request time, then by session end/start time
            query = query.order_by(
                desc(func.coalesce(latest_request_subq.c.latest_request_time, Session.ended_at, Session.started_at))
            )
            query = query.offset(offset).limit(limit)

            results = query.all()
            sessions = [r[0] for r in results]  # Extract Session objects from tuple

            return sessions, total

    # ============ Request operations ============

    def save_request(self, request: Request) -> Request:
        """Save a request."""
        with self.db_session() as db:
            db.add(request)
            db.commit()
            return request

    def get_request(self, request_id: str) -> Optional[Request]:
        """Get a request by ID."""
        with self.db_session() as db:
            return db.query(Request).filter_by(request_id=request_id).first()

    def get_requests_by_session(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Request]:
        """Get requests for a session."""
        with self.db_session() as db:
            return db.query(Request)\
                .filter_by(session_id=session_id)\
                .order_by(desc(Request.timestamp))\
                .offset(offset)\
                .limit(limit)\
                .all()

    def get_request_count_by_session(self, session_id: str) -> int:
        """Count requests for a session."""
        with self.db_session() as db:
            return db.query(Request).filter_by(session_id=session_id).count()

    # ============ Tool call operations ============

    def save_tool_call(self, tool_call: ToolCall) -> ToolCall:
        """Save a tool call."""
        with self.db_session() as db:
            db.add(tool_call)
            db.commit()
            return tool_call

    def get_tool_calls_by_request(self, request_id: str) -> List[Dict[str, Any]]:
        """Get tool calls for a request."""
        with self.db_session() as db:
            tool_calls = db.query(ToolCall).filter_by(request_id=request_id).all()
            return [tc.to_dict() for tc in tool_calls]

    # ============ Statistics operations ============

    def get_statistics_summary(self, hours: int = None, models: list = None) -> Dict[str, Any]:
        """Get overall statistics summary with optional model filter."""
        with self.db_session() as db:
            query = db.query(
                func.count(Request.id).label('total_requests'),
                func.sum(Request.input_tokens).label('total_input_tokens'),
                func.sum(Request.output_tokens).label('total_output_tokens'),
                func.sum(Request.cache_creation_tokens).label('cache_creation_tokens'),
                func.sum(Request.cache_read_tokens).label('cache_read_tokens'),
                func.sum(Request.cost).label('total_cost'),
                func.avg(Request.response_time_ms).label('avg_response_time_ms')
            )

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(Request.timestamp >= since)

            if models:
                query = query.filter(Request.model.in_(models))

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
                "cache_creation_tokens": result.cache_creation_tokens or 0,
                "cache_read_tokens": result.cache_read_tokens or 0,
                "total_cost": result.total_cost or 0.0,
                "avg_response_time_ms": result.avg_response_time_ms or 0.0,
            }

    def get_today_stats(self, models: list = None) -> Dict[str, Any]:
        """Get today's statistics with optional model filter."""
        with self.db_session() as db:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            query = db.query(
                func.count(Request.id).label('requests'),
                func.sum(Request.cost).label('cost')
            ).filter(Request.timestamp >= today)

            if models:
                query = query.filter(Request.model.in_(models))

            result = query.first()

            return {
                "requests": result.requests or 0,
                "cost": result.cost or 0.0
            }

    def get_timeline_stats(self, days: int = None, hours: int = None, minutes: int = None, models: list = None) -> List[Dict[str, Any]]:
        """Get request volume with configurable granularity and optional model filter.

        Args:
            days: Number of days for daily granularity
            hours: Number of hours for hourly granularity
            minutes: Number of minutes for minute granularity
            models: Optional list of models to filter by

        Returns:
            List of dicts with date/timestamp and count
        """
        with self.db_session() as db:
            # Determine granularity and time range
            if minutes:
                since = datetime.now() - timedelta(minutes=minutes)
                time_format = '%Y-%m-%dT%H:%M:00'
                label = 'timestamp'
            elif hours:
                since = datetime.now() - timedelta(hours=hours)
                time_format = '%Y-%m-%dT%H:00:00'
                label = 'timestamp'
            else:
                # Default to days
                days = days or 7
                since = datetime.now() - timedelta(days=days)
                time_format = None  # Use func.date for daily
                label = 'date'

            if time_format:
                # Hourly or minute granularity
                query = db.query(
                    func.strftime(time_format, Request.timestamp).label(label),
                    func.count(Request.id).label('count')
                ).filter(Request.timestamp >= since)

                if models:
                    query = query.filter(Request.model.in_(models))

                results = query.group_by(func.strftime(time_format, Request.timestamp))\
                    .order_by(func.strftime(time_format, Request.timestamp))\
                    .all()
                return [{label: r[0], "count": r[1]} for r in results]
            else:
                # Daily granularity
                query = db.query(
                    func.date(Request.timestamp).label(label),
                    func.count(Request.id).label('count')
                ).filter(Request.timestamp >= since)

                if models:
                    query = query.filter(Request.model.in_(models))

                results = query.group_by(func.date(Request.timestamp))\
                    .order_by(func.date(Request.timestamp))\
                    .all()
                return [{label: str(r.date), "count": r.count} for r in results]

    def get_model_distribution(self, hours: int = None) -> Dict[str, Dict[str, Any]]:
        """Get model usage distribution."""
        with self.db_session() as db:
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

    def get_usage_by_model(self) -> List[Dict[str, Any]]:
        """Get token usage by model."""
        with self.db_session() as db:
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

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.db_session() as db:
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

    def get_daily_costs(self) -> List[Dict[str, Any]]:
        """Get daily cost aggregation."""
        with self.db_session() as db:
            results = db.query(
                func.date(Request.timestamp).label('date'),
                func.sum(Request.cost).label('cost')
            ).group_by(func.date(Request.timestamp))\
                .order_by(desc(func.date(Request.timestamp)))\
                .limit(30).all()

            return [{"date": str(r.date), "cost": r.cost or 0.0} for r in results]

    def get_requests(self, limit: int = 1000) -> List[Request]:
        """Get requests list."""
        with self.db_session() as db:
            return db.query(Request).order_by(desc(Request.timestamp)).limit(limit).all()

    # ============ Tool usage operations ============

    def get_tool_usage_stats(self, hours: int = None) -> List[Any]:
        """Get tool usage statistics."""
        with self.db_session() as db:
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

    def get_tool_usage_by_hour(self) -> List[Dict[str, Any]]:
        """Get tool usage by hour."""
        with self.db_session() as db:
            results = db.query(
                func.strftime('%H', ToolCall.timestamp).label('hour'),
                func.count(ToolCall.id).label('count')
            ).group_by(func.strftime('%H', ToolCall.timestamp)).all()

            return [{"hour": int(r.hour), "count": r.count} for r in results]

    # ============ Analysis module compatibility ============

    def get_tool_usage_stats_with_time_filter(self, hours: int = None, models: list = None) -> List[Dict[str, Any]]:
        """Get tool usage stats with optional time and model filter (for ToolAnalyzer)."""
        with self.db_session() as db:
            query = db.query(
                ToolCall.tool_name,
                func.count(ToolCall.id).label('count'),
                func.avg(ToolCall.duration_ms).label('avg_duration_ms')
            )

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(ToolCall.timestamp >= since)

            if models:
                # Join with Request to filter by model
                query = query.join(Request, ToolCall.request_id == Request.request_id)
                query = query.filter(Request.model.in_(models))

            results = query.group_by(ToolCall.tool_name).all()

            return [
                {
                    "tool_name": r.tool_name,
                    "count": r.count,
                    "avg_duration_ms": r.avg_duration_ms or 0
                }
                for r in results
            ]

    def get_model_usage_stats_with_time_filter(self, hours: int = None) -> List[Dict[str, Any]]:
        """Get model usage stats with optional time filter (for StatisticsEngine)."""
        with self.db_session() as db:
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

    def get_model_usage_stats(self) -> List[Dict[str, Any]]:
        """Get model usage stats (for TokenAnalyzer)."""
        with self.db_session() as db:
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

    def get_session_count(self) -> int:
        """Get total session count (for StatisticsEngine)."""
        with self.db_session() as db:
            return db.query(func.count(Session.id)).scalar() or 0

    def get_avg_requests_per_session(self) -> float:
        """Get average requests per session (for StatisticsEngine)."""
        with self.db_session() as db:
            total_requests = db.query(func.count(Request.id)).scalar() or 0
            total_sessions = db.query(func.count(Session.id)).scalar() or 0
            if total_sessions == 0:
                return 0.0
            return total_requests / total_sessions

    def get_avg_tokens_per_session(self) -> float:
        """Get average tokens per session (for StatisticsEngine)."""
        with self.db_session() as db:
            total_input = db.query(func.sum(Request.input_tokens)).scalar() or 0
            total_output = db.query(func.sum(Request.output_tokens)).scalar() or 0
            total_sessions = db.query(func.count(Session.id)).scalar() or 0
            if total_sessions == 0:
                return 0.0
            return (total_input + total_output) / total_sessions

    # ============ Timing statistics ============

    def get_timing_statistics(self, hours: Optional[int] = None, models: list = None) -> Dict[str, Any]:
        """Get timing statistics for requests with optional model filter."""
        with self.db_session() as db:
            query = db.query(
                func.avg(Request.connect_ms).label('avg_connect_ms'),
                func.avg(Request.tls_ms).label('avg_tls_ms'),
                func.avg(Request.send_ms).label('avg_send_ms'),
                func.avg(Request.wait_ms).label('avg_wait_ms'),
                func.avg(Request.receive_ms).label('avg_receive_ms'),
                func.avg(Request.time_to_first_token_ms).label('avg_ttf_token_ms'),
                func.avg(Request.avg_token_latency_ms).label('avg_token_latency_ms'),
                func.avg(Request.response_time_ms).label('avg_response_time_ms'),
            )

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(Request.timestamp >= since)

            if models:
                query = query.filter(Request.model.in_(models))

            result = query.first()

            return {
                "avg_connect_ms": result.avg_connect_ms or 0,
                "avg_tls_ms": result.avg_tls_ms or 0,
                "avg_send_ms": result.avg_send_ms or 0,
                "avg_wait_ms": result.avg_wait_ms or 0,
                "avg_receive_ms": result.avg_receive_ms or 0,
                "avg_time_to_first_token_ms": result.avg_ttf_token_ms or 0,
                "avg_token_latency_ms": result.avg_token_latency_ms or 0,
                "avg_response_time_ms": result.avg_response_time_ms or 0,
            }

    def get_response_time_percentiles(self, hours: Optional[int] = None, models: list = None) -> Dict[str, float]:
        """Get response time percentiles (P50, P95, P99) with optional model filter."""
        with self.db_session() as db:
            query = db.query(Request.response_time_ms)

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(Request.timestamp >= since)

            if models:
                query = query.filter(Request.model.in_(models))

            results = query.all()
            times = [r[0] for r in results if r[0] is not None]

            if not times:
                return {"p50": 0, "p95": 0, "p99": 0}

            times.sort()
            n = len(times)

            def percentile(p: float) -> float:
                idx = int(n * p / 100)
                return times[min(idx, n - 1)]

            return {
                "p50": percentile(50),
                "p95": percentile(95),
                "p99": percentile(99),
            }

    def get_timing_breakdown_by_model(self, hours: Optional[int] = None, models: list = None) -> List[Dict[str, Any]]:
        """Get timing breakdown grouped by model with optional model filter."""
        with self.db_session() as db:
            query = db.query(
                Request.model,
                func.avg(Request.connect_ms).label('avg_connect_ms'),
                func.avg(Request.tls_ms).label('avg_tls_ms'),
                func.avg(Request.wait_ms).label('avg_wait_ms'),
                func.avg(Request.receive_ms).label('avg_receive_ms'),
                func.avg(Request.response_time_ms).label('avg_response_time_ms'),
                func.count(Request.id).label('request_count'),
            ).filter(Request.model.isnot(None))

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(Request.timestamp >= since)

            if models:
                query = query.filter(Request.model.in_(models))

            results = query.group_by(Request.model).all()

            return [
                {
                    "model": r.model,
                    "avg_connect_ms": r.avg_connect_ms or 0,
                    "avg_tls_ms": r.avg_tls_ms or 0,
                    "avg_wait_ms": r.avg_wait_ms or 0,
                    "avg_receive_ms": r.avg_receive_ms or 0,
                    "avg_response_time_ms": r.avg_response_time_ms or 0,
                    "request_count": r.request_count,
                }
                for r in results
            ]

    # ============ System Reminder Deduplication ============

    def save_system_reminder(self, content: str) -> str:
        """
        Save system-reminder content with deduplication.
        Returns the content_hash for reference.
        """
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:64]

        with self.db_session() as db:
            # Check if exists
            existing = db.query(SystemReminder).filter_by(content_hash=content_hash).first()
            if existing:
                existing.use_count += 1
                db.commit()
                return content_hash

            # Create new
            reminder = SystemReminder(
                content_hash=content_hash,
                content=content,
                first_seen_at=datetime.now(),
                use_count=1
            )
            db.add(reminder)
            db.commit()
            return content_hash

    def get_system_reminder(self, content_hash: str) -> Optional[SystemReminder]:
        """Get system-reminder by hash."""
        with self.db_session() as db:
            return db.query(SystemReminder).filter_by(content_hash=content_hash).first()

    def get_system_reminder_stats(self) -> Dict[str, Any]:
        """Get statistics about system-reminder deduplication."""
        with self.db_session() as db:
            total = db.query(func.count(SystemReminder.id)).scalar() or 0
            total_uses = db.query(func.sum(SystemReminder.use_count)).scalar() or 0
            total_bytes = db.query(func.sum(func.length(SystemReminder.content))).scalar() or 0

            # Calculate savings
            unique_content_size = total_bytes
            if total > 0:
                avg_size_per_reminder = total_bytes / total
                estimated_without_dedup = avg_size_per_reminder * total_uses
                savings_bytes = estimated_without_dedup - unique_content_size
                savings_percent = (savings_bytes / estimated_without_dedup * 100) if estimated_without_dedup > 0 else 0
            else:
                savings_bytes = 0
                savings_percent = 0

            return {
                "unique_count": total,
                "total_uses": total_uses,
                "unique_size_bytes": unique_content_size,
                "savings_bytes": int(savings_bytes),
                "savings_percent": round(savings_percent, 2),
            }

    # ============ URL Filter CRUD ============

    def get_url_filters(self, enabled_only: bool = False) -> List[UrlFilter]:
        """Get all URL filters, optionally only enabled ones."""
        with self.db_session() as db:
            query = db.query(UrlFilter)
            if enabled_only:
                query = query.filter(UrlFilter.is_enabled == True)
            return query.order_by(UrlFilter.priority.asc()).all()

    def add_url_filter(self, filter_data: Dict[str, Any]) -> UrlFilter:
        """Add a new URL filter."""
        with self.db_session() as db:
            filter_rule = UrlFilter(
                name=filter_data.get('name', ''),
                pattern=filter_data.get('pattern', ''),
                filter_type=filter_data.get('filter_type', 'domain'),
                action=filter_data.get('action', 'include'),
                priority=filter_data.get('priority', 100),
                is_enabled=filter_data.get('is_enabled', True),
            )
            db.add(filter_rule)
            db.commit()
            db.refresh(filter_rule)
            return filter_rule

    def update_url_filter(self, filter_id: int, filter_data: Dict[str, Any]) -> Optional[UrlFilter]:
        """Update an existing URL filter."""
        with self.db_session() as db:
            filter_rule = db.query(UrlFilter).filter_by(id=filter_id).first()
            if not filter_rule:
                return None

            for key, value in filter_data.items():
                if hasattr(filter_rule, key):
                    setattr(filter_rule, key, value)

            db.commit()
            db.refresh(filter_rule)
            return filter_rule

    def delete_url_filter(self, filter_id: int) -> bool:
        """Delete a URL filter."""
        with self.db_session() as db:
            filter_rule = db.query(UrlFilter).filter_by(id=filter_id).first()
            if not filter_rule:
                return False
            db.delete(filter_rule)
            db.commit()
            return True

    def check_url_allowed(self, url: str) -> bool:
        """Check if URL should be captured based on filter rules."""
        import re
        import fnmatch

        filters = self.get_url_filters(enabled_only=True)

        for filter_rule in sorted(filters, key=lambda f: f.priority):
            matched = False

            if filter_rule.filter_type == 'domain':
                matched = filter_rule.pattern.lower() in url.lower()
            elif filter_rule.filter_type == 'path':
                matched = filter_rule.pattern in url
            elif filter_rule.filter_type == 'exact':
                matched = url == filter_rule.pattern
            elif filter_rule.filter_type == 'wildcard':
                matched = fnmatch.fnmatch(url, filter_rule.pattern)
            elif filter_rule.filter_type == 'regex':
                try:
                    matched = bool(re.search(filter_rule.pattern, url))
                except re.error:
                    continue

            if matched:
                return filter_rule.action == 'include'

        # Default: deny if no matching filter
        return False

    def test_url_filter(self, pattern: str, filter_type: str, url: str) -> bool:
        """Test if a URL matches a filter pattern without saving."""
        import re
        import fnmatch

        if filter_type == 'domain':
            return pattern.lower() in url.lower()
        elif filter_type == 'path':
            return pattern in url
        elif filter_type == 'exact':
            return url == pattern
        elif filter_type == 'wildcard':
            return fnmatch.fnmatch(url, filter_pattern)
        elif filter_type == 'regex':
            try:
                return bool(re.search(pattern, url))
            except re.error:
                return False
        return False

    # ============ Success Rate Statistics ============

    def get_success_rate_stats(self, hours: Optional[int] = None, models: list = None) -> Dict[str, Any]:
        """
        Get success rate statistics for requests with optional model filter.

        Success is defined as response_status in 200-299 range.
        Only counts requests that match URL filter rules.

        Args:
            hours: Optional time filter (last N hours)
            models: Optional list of models to filter by

        Returns:
            Dict with total_requests, successful_requests, failed_requests, success_rate
        """
        import re
        import fnmatch

        with self.db_session() as db:
            # Get all enabled include filters
            filters = db.query(UrlFilter).filter(
                UrlFilter.is_enabled == True,
                UrlFilter.action == 'include'
            ).order_by(UrlFilter.priority.asc()).all()

            # Build filter conditions for URL matching
            # We need to check request_body for the actual URL since Request doesn't have a url column
            # The URL is typically in the request_body as part of the proxy capture

            # Get base query
            query = db.query(
                func.count(Request.id).label('total'),
                func.count(Request.id).filter(
                    Request.response_status.between(200, 299)
                ).label('successful')
            )

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                query = query.filter(Request.timestamp >= since)

            if models:
                query = query.filter(Request.model.in_(models))

            # Execute query
            result = query.first()
            total = result.total or 0
            successful = result.successful or 0
            failed = total - successful

            # Calculate success rate
            success_rate = (successful / total * 100) if total > 0 else 0

            # Get breakdown by status code ranges
            from sqlalchemy import case
            status_breakdown = db.query(
                case(
                    (Request.response_status.between(200, 299), '2xx'),
                    (Request.response_status.between(300, 399), '3xx'),
                    (Request.response_status.between(400, 499), '4xx'),
                    (Request.response_status.between(500, 599), '5xx'),
                    else_='other'
                ).label('status_range'),
                func.count(Request.id).label('count')
            )

            if hours:
                since = datetime.now() - timedelta(hours=hours)
                status_breakdown = status_breakdown.filter(Request.timestamp >= since)

            if models:
                status_breakdown = status_breakdown.filter(Request.model.in_(models))

            status_breakdown = status_breakdown.group_by('status_range').all()

            breakdown = {r.status_range: r.count for r in status_breakdown}

            return {
                "total_requests": total,
                "successful_requests": successful,
                "failed_requests": failed,
                "success_rate": round(success_rate, 2),
                "breakdown": {
                    "2xx": breakdown.get('2xx', 0),
                    "3xx": breakdown.get('3xx', 0),
                    "4xx": breakdown.get('4xx', 0),
                    "5xx": breakdown.get('5xx', 0),
                    "other": breakdown.get('other', 0)
                }
            }

    def _get_aggregated_stats(self, period_type: str, period_start: datetime) -> Optional[Statistics]:
        """
        Get pre-aggregated statistics for a specific period.

        Args:
            period_type: 'hour' or 'day'
            period_start: Start of the period

        Returns:
            Statistics record or None
        """
        with self.db_session() as db:
            return db.query(Statistics).filter_by(
                period_type=period_type,
                period_start=period_start
            ).first()

    def get_aggregated_stats_range(self, period_type: str, start: datetime, end: datetime) -> List[Statistics]:
        """
        Get pre-aggregated statistics for a range of periods.

        Args:
            period_type: 'hour' or 'day'
            start: Start of the range
            end: End of the range

        Returns:
            List of Statistics records
        """
        with self.db_session() as db:
            return db.query(Statistics).filter(
                Statistics.period_type == period_type,
                Statistics.period_start >= start,
                Statistics.period_start < end
            ).order_by(Statistics.period_start).all()
