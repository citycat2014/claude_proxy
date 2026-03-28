"""
Flask web application for visualization.

Provides a web interface for viewing captured interactions,
statistics, and analysis reports.
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask import Flask
import os
import sys
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DATABASE_PATH, WEB_HOST, WEB_PORT, DEBUG
from storage.database import Database
from analysis.token_analyzer import TokenAnalyzer
from analysis.tool_analyzer import ToolAnalyzer
from analysis.statistics import StatisticsEngine

# Configuration
USE_VUE = os.environ.get('USE_VUE', 'false').lower() == 'true'
VUE_DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'vue-dist')


def format_datetime(dt) -> str:
    """Convert datetime to ISO format for JS parsing."""
    if dt is None:
        return None
    if isinstance(dt, str):
        # If it's already a string, convert to ISO format
        return dt.replace(' ', 'T')
    # If it's a datetime object
    return dt.isoformat()


def extract_user_input_preview(messages_json: str, max_length: int = 200) -> str:
    """Extract actual user input from messages, filtering system-reminders."""
    try:
        messages = json.loads(messages_json or '[]')
        # Find the last user message (most recent)
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                content = msg.get('content', '')
                # Handle array content (filter system-reminders)
                if isinstance(content, list):
                    actual_text = []
                    for block in content:
                        if isinstance(block, dict) and block.get('text'):
                            text = block['text']
                            # Skip system-reminder blocks
                            if not text.startswith('<system-reminder>'):
                                actual_text.append(text)
                        elif isinstance(block, str):
                            if not block.startswith('<system-reminder>'):
                                actual_text.append(block)
                    content = ' '.join(actual_text)
                # Handle string content
                elif isinstance(content, str):
                    # Remove system-reminder sections
                    while '<system-reminder>' in content and '</system-reminder>' in content:
                        start = content.find('<system-reminder>')
                        end = content.find('</system-reminder>') + len('</system-reminder>')
                        content = content[:start] + content[end:]
                    content = content.strip()

                if content:
                    if len(content) > max_length:
                        return content[:max_length] + '...'
                    return content
        return "No user input"
    except Exception:
        return "Error parsing input"


def serialize_session(session):
    """Convert session object to JSON-serializable dict with formatted timestamps."""
    return {
        "id": session.id,
        "session_id": session.session_id,
        "started_at": format_datetime(session.started_at),
        "ended_at": format_datetime(session.ended_at),
        "total_requests": session.total_requests,
        "total_input_tokens": session.total_input_tokens,
        "total_output_tokens": session.total_output_tokens,
        "total_cost": session.total_cost,
        "model": session.model,
        "user_agent": session.user_agent,
        "working_directory": session.working_directory,
    }


def serialize_request(req, include_tool_calls: bool = False):
    """Convert request object to JSON-serializable dict with formatted timestamps."""
    data = {
        "id": req.id,
        "request_id": req.request_id,
        "session_id": req.session_id,
        "timestamp": format_datetime(req.timestamp),
        "method": req.method,
        "endpoint": req.endpoint,
        "model": req.model,
        "system_prompt": req.system_prompt,
        "messages_json": req.messages_json,
        "response_status": req.response_status,
        "response_time_ms": req.response_time_ms,
        "is_streaming": req.is_streaming,
        "input_tokens": req.input_tokens,
        "output_tokens": req.output_tokens,
        "cache_creation_tokens": req.cache_creation_tokens,
        "cache_read_tokens": req.cache_read_tokens,
        "cost": req.cost,
        "request_body": req.request_body,
        "response_body": req.response_body,
        "response_text": req.response_text,
        "response_thinking": req.response_thinking,
        "user_input_preview": extract_user_input_preview(req.messages_json),
    }

    if include_tool_calls:
        tool_calls = db.get_tool_calls_by_request(req.request_id)
        data["tool_calls"] = tool_calls

    return data

# Create Flask app
app = Flask(__name__,
            template_folder="templates",
            static_folder="static")

# Initialize components
db = Database(DATABASE_PATH)
token_analyzer = TokenAnalyzer(db)
tool_analyzer = ToolAnalyzer(db)
stats_engine = StatisticsEngine(db)


# ============================================================================
# Page Routes
# ============================================================================

@app.route("/")
def index():
    """Dashboard page."""
    if USE_VUE and os.path.exists(VUE_DIST_DIR):
        return send_from_directory(VUE_DIST_DIR, 'index.html')
    return render_template("index.html")


@app.route("/sessions")
def sessions():
    """Sessions list page."""
    if USE_VUE and os.path.exists(VUE_DIST_DIR):
        return send_from_directory(VUE_DIST_DIR, 'index.html')
    return render_template("sessions.html")


@app.route("/sessions/<session_id>")
def session_detail(session_id):
    """Session detail page."""
    if USE_VUE and os.path.exists(VUE_DIST_DIR):
        return send_from_directory(VUE_DIST_DIR, 'index.html')
    return render_template("session_detail.html", session_id=session_id)


@app.route("/requests/<request_id>")
def request_detail(request_id):
    """Request detail page."""
    if USE_VUE and os.path.exists(VUE_DIST_DIR):
        return send_from_directory(VUE_DIST_DIR, 'index.html')
    return render_template("request_detail.html", request_id=request_id)


@app.route("/analysis")
def analysis():
    """Analysis page."""
    if USE_VUE and os.path.exists(VUE_DIST_DIR):
        return send_from_directory(VUE_DIST_DIR, 'index.html')
    return render_template("analysis.html")


# Serve Vue static assets
@app.route('/assets/<path:filename>')
def serve_vue_assets(filename):
    """Serve Vue assets."""
    if USE_VUE and os.path.exists(VUE_DIST_DIR):
        return send_from_directory(os.path.join(VUE_DIST_DIR, 'assets'), filename)
    return jsonify({"error": "Not found"}), 404


# ============================================================================
# API Routes
# ============================================================================

@app.route("/api/statistics/summary")
def api_statistics_summary():
    """Get summary statistics with optional time filter."""
    hours = request.args.get("hours", None, type=int)
    summary = stats_engine.get_summary(hours=hours)
    return jsonify({
        "total_requests": summary.total_requests,
        "total_sessions": summary.total_sessions,
        "total_input_tokens": summary.total_input_tokens,
        "total_output_tokens": summary.total_output_tokens,
        "total_cost": summary.total_cost,
        "avg_response_time_ms": summary.avg_response_time_ms,
        "requests_today": summary.requests_today,
        "cost_today": summary.cost_today,
    })


@app.route("/api/statistics/timeline")
def api_statistics_timeline():
    """Get timeline statistics with optional time filter."""
    hours = request.args.get("hours", None, type=int)
    days = request.args.get("days", None, type=int)
    timeline = stats_engine.get_request_volume_timeline(hours=hours, days=days)
    return jsonify(timeline)


@app.route("/api/statistics/models")
def api_statistics_models():
    """Get model distribution with optional time filter."""
    hours = request.args.get("hours", None, type=int)
    distribution = stats_engine.get_model_distribution(hours=hours)
    return jsonify(distribution)


@app.route("/api/statistics/tools")
def api_statistics_tools():
    """Get tool usage statistics with optional time filter."""
    hours = request.args.get("hours", None, type=int)
    stats = tool_analyzer.get_tool_usage_stats(hours=hours)
    return jsonify([
        {
            "name": s.name,
            "calls": s.total_calls,
            "avg_duration_ms": s.avg_duration_ms,
        }
        for s in stats
    ])


@app.route("/api/sessions")
def api_sessions():
    """Get sessions list with filtering."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Get filter parameters
    session_id = request.args.get("session_id", None)
    model = request.args.get("model", None)
    date_from = request.args.get("date_from", None)
    date_to = request.args.get("date_to", None)

    sessions, total = db.get_sessions(
        limit=per_page, offset=(page - 1) * per_page,
        session_id_filter=session_id,
        model_filter=model,
        date_from=date_from,
        date_to=date_to
    )

    return jsonify({
        "sessions": [serialize_session(s) for s in sessions],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
    })


@app.route("/api/sessions/<session_id>")
def api_session_detail(session_id):
    """Get session details with paginated requests."""
    session = db.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    # Limit per_page to reasonable range
    per_page = min(max(per_page, 5), 100)

    offset = (page - 1) * per_page
    requests_list = db.get_requests_by_session(session_id, limit=per_page, offset=offset)
    total_requests = db.get_request_count_by_session(session_id)

    return jsonify({
        "session": serialize_session(session),
        "requests": [serialize_request(r, include_tool_calls=True) for r in requests_list],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_requests,
            "total_pages": (total_requests + per_page - 1) // per_page
        }
    })


@app.route("/api/requests/<request_id>")
def api_request_detail(request_id):
    """Get request details."""
    req = db.get_request(request_id)
    if not req:
        return jsonify({"error": "Request not found"}), 404

    tool_calls = db.get_tool_calls_by_request(request_id)

    return jsonify({
        "request": serialize_request(req),
        "tool_calls": tool_calls,
    })


@app.route("/api/analysis/tokens")
def api_analysis_tokens():
    """Get token analysis."""
    usage = token_analyzer.get_overall_usage()
    by_model = token_analyzer.get_usage_by_model()
    efficiency = token_analyzer.get_efficiency_metrics()
    monthly_estimate = token_analyzer.estimate_monthly_cost()

    return jsonify({
        "overall": {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
            "cost": usage.cost,
        },
        "by_model": {
            model: {
                "input_tokens": u.input_tokens,
                "output_tokens": u.output_tokens,
                "total_tokens": u.total_tokens,
                "cost": u.cost,
            }
            for model, u in by_model.items()
        },
        "efficiency": efficiency,
        "monthly_estimate": monthly_estimate,
    })


@app.route("/api/analysis/tools")
def api_analysis_tools():
    """Get tool analysis."""
    distribution = tool_analyzer.get_tool_usage_distribution()
    categories = tool_analyzer.get_tool_category_distribution()
    most_used = tool_analyzer.get_most_used_tools()
    slowest = tool_analyzer.get_slowest_tools()
    patterns = tool_analyzer.analyze_tool_patterns()

    return jsonify({
        "distribution": distribution,
        "categories": categories,
        "most_used": most_used,
        "slowest": slowest,
        "patterns": patterns,
    })


@app.route("/api/export/sessions")
def api_export_sessions():
    """Export sessions data."""
    format = request.args.get("format", "json")
    sessions = db.get_sessions(limit=1000)

    if format == "json":
        return jsonify(sessions)
    else:
        return jsonify({"error": "Unsupported format"}), 400


@app.route("/api/export/session/<session_id>")
def api_export_session(session_id):
    """Export a single session."""
    session = db.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    requests = db.get_requests_by_session(session_id)

    return jsonify({
        "session": session,
        "requests": requests,
    })


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


# ============================================================================
# Main
# ============================================================================

def main():
    """Run the Flask application."""
    print(f"Starting web server at http://{WEB_HOST}:{WEB_PORT}")
    print(f"Database: {DATABASE_PATH}")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=DEBUG)


if __name__ == "__main__":
    main()