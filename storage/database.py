"""
Database operations for pkts_capture.

Handles SQLite connection, schema initialization, and CRUD operations.
"""

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from storage.models import Session, Request, ToolCall, Message, Statistics


SCHEMA = """
-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_requests INTEGER DEFAULT 0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0.0,
    model TEXT,
    user_agent TEXT,
    working_directory TEXT
);

-- Requests table
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE NOT NULL,
    session_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    method TEXT,
    endpoint TEXT,
    model TEXT,
    system_prompt TEXT,
    messages_json TEXT,
    response_status INTEGER,
    response_time_ms INTEGER,
    is_streaming BOOLEAN DEFAULT FALSE,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cost REAL DEFAULT 0.0,
    request_body TEXT,
    response_body TEXT,
    response_text TEXT,
    response_thinking TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Tool calls table
CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_input_json TEXT,
    tool_result TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    FOREIGN KEY (request_id) REFERENCES requests(request_id)
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content_type TEXT,
    content_text TEXT,
    sequence INTEGER,
    FOREIGN KEY (request_id) REFERENCES requests(request_id)
);

-- Statistics table
CREATE TABLE IF NOT EXISTS statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_type TEXT,
    period_start TIMESTAMP,
    request_count INTEGER DEFAULT 0,
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0.0,
    avg_response_time_ms REAL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_requests_session ON requests(session_id);
CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_tool_calls_request ON tool_calls(request_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_name ON tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_messages_request ON messages(request_id);
"""


class Database:
    """SQLite database handler."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
        self.init_db()

    def _ensure_db_dir(self):
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ============ Session operations ============

    def upsert_session(self, session: Session) -> Session:
        """Insert or update a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if session exists
            cursor.execute(
                "SELECT id FROM sessions WHERE session_id = ?",
                (session.session_id,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing session
                cursor.execute("""
                    UPDATE sessions SET
                        ended_at = ?,
                        total_requests = ?,
                        total_input_tokens = ?,
                        total_output_tokens = ?,
                        total_cost = ?,
                        model = ?
                    WHERE session_id = ?
                """, (
                    session.ended_at,
                    session.total_requests,
                    session.total_input_tokens,
                    session.total_output_tokens,
                    session.total_cost,
                    session.model,
                    session.session_id,
                ))
                session.id = existing["id"]
            else:
                # Insert new session
                cursor.execute("""
                    INSERT INTO sessions (
                        session_id, started_at, user_agent, working_directory
                    ) VALUES (?, ?, ?, ?)
                """, (
                    session.session_id,
                    session.started_at or datetime.now(),
                    session.user_agent,
                    session.working_directory,
                ))
                session.id = cursor.lastrowid

            conn.commit()
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_session(row)
            return None

    def get_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "started_at DESC",
        session_id_filter: str = None,
        model_filter: str = None,
        date_from: str = None,
        date_to: str = None
    ) -> List[Session]:
        """Get list of sessions with optional filtering."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build WHERE clause
            conditions = []
            params = []

            if session_id_filter:
                # Check if it looks like a request ID (starts with 'req_')
                if session_id_filter.startswith('req_'):
                    # Find sessions that have this request
                    cursor.execute("""
                        SELECT DISTINCT s.* FROM sessions s
                        JOIN requests r ON s.session_id = r.session_id
                        WHERE r.request_id LIKE ?
                        ORDER BY s.started_at DESC
                        LIMIT ? OFFSET ?
                    """, (f"%{session_id_filter}%", limit, offset))
                    sessions = [self._row_to_session(row) for row in cursor.fetchall()]

                    # Get total count
                    cursor.execute("""
                        SELECT COUNT(DISTINCT s.session_id) FROM sessions s
                        JOIN requests r ON s.session_id = r.session_id
                        WHERE r.request_id LIKE ?
                    """, (f"%{session_id_filter}%",))
                    total = cursor.fetchone()[0]
                    return sessions, total
                else:
                    # Regular session_id search
                    conditions.append("session_id LIKE ?")
                    params.append(f"%{session_id_filter}%")

            if model_filter:
                conditions.append("model LIKE ?")
                params.append(f"%{model_filter}%")

            if date_from:
                conditions.append("started_at >= ?")
                params.append(date_from)

            if date_to:
                conditions.append("started_at <= ?")
                params.append(f"{date_to} 23:59:59")

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Get total count for filtered results
            count_sql = f"SELECT COUNT(*) FROM sessions {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]

            # Get paginated results
            sql = f"SELECT * FROM sessions {where_clause} ORDER BY {order_by} LIMIT ? OFFSET ?"
            cursor.execute(sql, params + [limit, offset])

            return [self._row_to_session(row) for row in cursor.fetchall()], total

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        """Convert a database row to a Session object."""
        return Session(
            id=row["id"],
            session_id=row["session_id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            total_requests=row["total_requests"],
            total_input_tokens=row["total_input_tokens"],
            total_output_tokens=row["total_output_tokens"],
            total_cost=row["total_cost"],
            model=row["model"],
            user_agent=row["user_agent"],
            working_directory=row["working_directory"],
        )

    # ============ Request operations ============

    def save_request(self, request: Request) -> Request:
        """Save a request to the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO requests (
                    request_id, session_id, timestamp, method, endpoint,
                    model, system_prompt, messages_json,
                    response_status, response_time_ms, is_streaming,
                    input_tokens, output_tokens,
                    cache_creation_tokens, cache_read_tokens,
                    cost, request_body, response_body, response_text, response_thinking
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.request_id,
                request.session_id,
                request.timestamp or datetime.now(),
                request.method,
                request.endpoint,
                request.model,
                request.system_prompt,
                request.messages_json,
                request.response_status,
                request.response_time_ms,
                request.is_streaming,
                request.input_tokens,
                request.output_tokens,
                request.cache_creation_tokens,
                request.cache_read_tokens,
                request.cost,
                request.request_body,
                request.response_body,
                request.response_text,
                request.response_thinking,
            ))
            request.id = cursor.lastrowid
            conn.commit()
            return request

    def get_request(self, request_id: str) -> Optional[Request]:
        """Get a request by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM requests WHERE request_id = ?",
                (request_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_request(row)
            return None

    def get_requests_by_session(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Request]:
        """Get requests for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM requests
                   WHERE session_id = ?
                   ORDER BY timestamp DESC
                   LIMIT ? OFFSET ?""",
                (session_id, limit, offset)
            )
            return [self._row_to_request(row) for row in cursor.fetchall()]

    def get_request_count_by_session(self, session_id: str) -> int:
        """Get total request count for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM requests WHERE session_id = ?",
                (session_id,)
            )
            return cursor.fetchone()[0]

    def _row_to_request(self, row: sqlite3.Row) -> Request:
        """Convert a database row to a Request object."""
        return Request(
            id=row["id"],
            request_id=row["request_id"],
            session_id=row["session_id"],
            timestamp=row["timestamp"],
            method=row["method"],
            endpoint=row["endpoint"],
            model=row["model"],
            system_prompt=row["system_prompt"],
            messages_json=row["messages_json"],
            response_status=row["response_status"],
            response_time_ms=row["response_time_ms"],
            is_streaming=bool(row["is_streaming"]),
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            cache_creation_tokens=row["cache_creation_tokens"],
            cache_read_tokens=row["cache_read_tokens"],
            cost=row["cost"],
            request_body=row["request_body"],
            response_body=row["response_body"],
            response_text=row["response_text"] if "response_text" in row.keys() else "",
            response_thinking=row["response_thinking"] if "response_thinking" in row.keys() else "",
        )

    # ============ Tool call operations ============

    def save_tool_call(self, tool_call: ToolCall) -> ToolCall:
        """Save a tool call to the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO tool_calls (
                    request_id, tool_name, tool_input_json,
                    tool_result, timestamp, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                tool_call.request_id,
                tool_call.tool_name,
                tool_call.tool_input_json,
                tool_call.tool_result,
                tool_call.timestamp or datetime.now(),
                tool_call.duration_ms,
            ))
            tool_call.id = cursor.lastrowid
            conn.commit()
            return tool_call

    def get_tool_calls_by_request(self, request_id: str) -> List[ToolCall]:
        """Get tool calls for a request."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tool_calls WHERE request_id = ? ORDER BY timestamp",
                (request_id,)
            )
            return [self._row_to_tool_call(row) for row in cursor.fetchall()]

    def _row_to_tool_call(self, row: sqlite3.Row) -> ToolCall:
        """Convert a database row to a ToolCall object."""
        return ToolCall(
            id=row["id"],
            request_id=row["request_id"],
            tool_name=row["tool_name"],
            tool_input_json=row["tool_input_json"],
            tool_result=row["tool_result"],
            timestamp=row["timestamp"],
            duration_ms=row["duration_ms"],
        )

    # ============ Message operations ============

    def save_message(self, message: Message) -> Message:
        """Save a message to the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO messages (
                    request_id, role, content_type, content_text, sequence
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                message.request_id,
                message.role,
                message.content_type,
                message.content_text,
                message.sequence,
            ))
            message.id = cursor.lastrowid
            conn.commit()
            return message

    def get_messages_by_request(self, request_id: str) -> List[Message]:
        """Get messages for a request."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM messages WHERE request_id = ? ORDER BY sequence",
                (request_id,)
            )
            return [self._row_to_message(row) for row in cursor.fetchall()]

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        """Convert a database row to a Message object."""
        return Message(
            id=row["id"],
            request_id=row["request_id"],
            role=row["role"],
            content_type=row["content_type"],
            content_text=row["content_text"],
            sequence=row["sequence"],
        )

    # ============ Statistics operations ============

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get overall summary statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Overall stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total_requests,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(cost), 0) as total_cost,
                    COALESCE(AVG(response_time_ms), 0) as avg_response_time
                FROM requests
            """)
            overall = dict(cursor.fetchone())

            # Session count
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            overall["total_sessions"] = cursor.fetchone()["count"]

            # Today's stats
            cursor.execute("""
                SELECT
                    COUNT(*) as count,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COALESCE(SUM(cost), 0) as cost
                FROM requests
                WHERE date(timestamp) = date('now')
            """)
            today = cursor.fetchone()
            overall["today_requests"] = today["count"]
            overall["today_input_tokens"] = today["input_tokens"]
            overall["today_output_tokens"] = today["output_tokens"]
            overall["today_cost"] = today["cost"]

            return overall

    def get_tool_usage_stats(self) -> List[Dict[str, Any]]:
        """Get tool usage statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    tool_name,
                    COUNT(*) as count,
                    COALESCE(AVG(duration_ms), 0) as avg_duration_ms
                FROM tool_calls
                GROUP BY tool_name
                ORDER BY count DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_model_usage_stats(self) -> List[Dict[str, Any]]:
        """Get model usage statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    model,
                    COUNT(*) as count,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(cost), 0) as total_cost
                FROM requests
                WHERE model IS NOT NULL AND model != ''
                GROUP BY model
                ORDER BY count DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def get_timeline_stats(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily statistics for the last N days (using local timezone)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    date(timestamp, 'localtime') as date,
                    COUNT(*) as requests,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COALESCE(SUM(cost), 0) as cost
                FROM requests
                WHERE timestamp >= datetime('now', 'localtime', ?)
                GROUP BY date(timestamp, 'localtime')
                ORDER BY date ASC
            """, (f"-{days} days",))
            return [dict(row) for row in cursor.fetchall()]

    def get_summary_stats_with_time_filter(self, hours: Optional[int] = None) -> Dict[str, Any]:
        """Get summary statistics with optional time filter in hours."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build time filter
            time_condition = ""
            params = []
            if hours:
                time_condition = "WHERE timestamp >= datetime('now', 'localtime', ?)"
                params.append(f"-{hours} hours")

            # Overall stats
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_requests,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(cost), 0) as total_cost,
                    COALESCE(AVG(response_time_ms), 0) as avg_response_time
                FROM requests
                {time_condition}
            """, params)
            overall = dict(cursor.fetchone())

            # Session count with time filter
            if hours:
                cursor.execute("""
                    SELECT COUNT(DISTINCT s.session_id) as count
                    FROM sessions s
                    JOIN requests r ON s.session_id = r.session_id
                    WHERE r.timestamp >= datetime('now', 'localtime', ?)
                """, (f"-{hours} hours",))
            else:
                cursor.execute("SELECT COUNT(*) as count FROM sessions")
            overall["total_sessions"] = cursor.fetchone()["count"]

            return overall

    def get_model_usage_stats_with_time_filter(self, hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get model usage statistics with optional time filter."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            time_condition = ""
            params = []
            if hours:
                time_condition = "AND timestamp >= datetime('now', 'localtime', ?)"
                params.append(f"-{hours} hours")

            cursor.execute(f"""
                SELECT
                    model,
                    COUNT(*) as count,
                    COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                    COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                    COALESCE(SUM(cost), 0) as total_cost
                FROM requests
                WHERE model IS NOT NULL AND model != ''
                {time_condition}
                GROUP BY model
                ORDER BY count DESC
            """, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_tool_usage_stats_with_time_filter(self, hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get tool usage statistics with optional time filter."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            time_condition = ""
            params = []
            if hours:
                time_condition = "AND r.timestamp >= datetime('now', 'localtime', ?)"
                params.append(f"-{hours} hours")

            cursor.execute(f"""
                SELECT
                    t.tool_name,
                    COUNT(*) as count,
                    COALESCE(AVG(t.duration_ms), 0) as avg_duration_ms
                FROM tool_calls t
                JOIN requests r ON t.request_id = r.request_id
                WHERE 1=1
                {time_condition}
                GROUP BY t.tool_name
                ORDER BY count DESC
            """, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_timeline_stats_hourly(self, hours: int = 5) -> List[Dict[str, Any]]:
        """Get hourly statistics for the last N hours."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    strftime('%Y-%m-%d %H:00', timestamp, 'localtime') as hour,
                    COUNT(*) as requests,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COALESCE(SUM(cost), 0) as cost
                FROM requests
                WHERE timestamp >= datetime('now', 'localtime', ?)
                GROUP BY strftime('%Y-%m-%d %H', timestamp, 'localtime')
                ORDER BY hour ASC
            """, (f"-{hours} hours",))
            return [dict(row) for row in cursor.fetchall()]

    def get_timeline_stats_minute(self, minutes: int = 30) -> List[Dict[str, Any]]:
        """Get minute-level statistics for the last N minutes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    strftime('%Y-%m-%d %H:%M', timestamp, 'localtime') as minute,
                    COUNT(*) as requests,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COALESCE(SUM(cost), 0) as cost
                FROM requests
                WHERE timestamp >= datetime('now', 'localtime', ?)
                GROUP BY strftime('%Y-%m-%d %H:%M', timestamp, 'localtime')
                ORDER BY minute ASC
            """, (f"-{minutes} minutes",))
            return [dict(row) for row in cursor.fetchall()]

    def clear_all_data(self):
        """Clear all data from the database."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM tool_calls")
            conn.execute("DELETE FROM requests")
            conn.execute("DELETE FROM sessions")
            conn.execute("DELETE FROM statistics")
            conn.commit()

    def get_session_count(self) -> int:
        """Get total session count."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            return cursor.fetchone()["count"]

    def get_avg_requests_per_session(self) -> float:
        """Get average requests per session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(AVG(total_requests), 0) as avg
                FROM sessions
            """)
            return cursor.fetchone()["avg"]

    def get_avg_tokens_per_session(self) -> float:
        """Get average tokens per session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COALESCE(AVG(total_input_tokens + total_output_tokens), 0) as avg
                FROM sessions
            """)
            return cursor.fetchone()["avg"]

    def get_today_stats(self) -> Dict[str, Any]:
        """Get today's statistics (using local timezone)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as requests,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COALESCE(SUM(cost), 0) as cost
                FROM requests
                WHERE date(timestamp, 'localtime') = date('now', 'localtime')
            """)
            return dict(cursor.fetchone())