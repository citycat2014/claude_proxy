"""
Comprehensive tests for the Flask web application.

Run with: pytest tests/test_web.py -v
"""

import pytest
import json
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import app, format_datetime, extract_user_input_preview, serialize_session, serialize_request
from storage.models import Session, Request, ToolCall


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_session():
    """Create a mock Session object."""
    return Session(
        id=1,
        session_id="sess_test123",
        started_at=datetime(2024, 3, 28, 10, 0, 0),
        ended_at=datetime(2024, 3, 28, 11, 0, 0),
        total_requests=10,
        total_input_tokens=5000,
        total_output_tokens=2000,
        total_cost=0.5,
        model="claude-3-opus",
        user_agent="Claude Code",
        working_directory="/home/user/project"
    )


@pytest.fixture
def mock_request():
    """Create a mock Request object."""
    return Request(
        id=1,
        request_id="req_test456",
        session_id="sess_test123",
        timestamp=datetime(2024, 3, 28, 10, 30, 0),
        method="POST",
        endpoint="/v1/messages",
        model="claude-3-opus-20240229",
        system_prompt="You are Claude",
        messages_json=json.dumps([
            {"role": "user", "content": "Hello, how are you?"}
        ]),
        response_status=200,
        response_time_ms=1500,
        is_streaming=True,
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=10,
        cache_read_tokens=20,
        cost=0.01,
        request_body="{}",
        response_body="{}",
        response_text="I'm doing well, thank you!",
        response_thinking="The user is greeting me..."
    )


@pytest.fixture
def mock_tool_call():
    """Create a mock ToolCall object."""
    return {
        "id": 1,
        "request_id": "req_test456",
        "tool_name": "Glob",
        "tool_input": {"pattern": "**/*.py"},
        "tool_result": "[file1.py, file2.py]",
        "duration_ms": 100
    }


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Test helper functions."""

    def test_format_datetime_with_datetime(self):
        """Test format_datetime with datetime object."""
        dt = datetime(2024, 3, 28, 10, 30, 0)
        result = format_datetime(dt)
        assert result == "2024-03-28T10:30:00"

    def test_format_datetime_with_string(self):
        """Test format_datetime with string input."""
        dt_str = "2024-03-28 10:30:00"
        result = format_datetime(dt_str)
        assert result == "2024-03-28T10:30:00"

    def test_format_datetime_with_none(self):
        """Test format_datetime with None."""
        result = format_datetime(None)
        assert result is None

    def test_extract_user_input_preview_simple(self):
        """Test extract_user_input_preview with simple user message."""
        messages = json.dumps([
            {"role": "user", "content": "Hello, how are you?"}
        ])
        result = extract_user_input_preview(messages)
        assert result == "Hello, how are you?"

    def test_extract_user_input_preview_with_system_reminder(self):
        """Test filtering system-reminder from content."""
        messages = json.dumps([
            {"role": "user", "content": "<system-reminder>Some context</system-reminder>Hello there!"}
        ])
        result = extract_user_input_preview(messages)
        assert "system-reminder" not in result
        assert "Hello there!" in result

    def test_extract_user_input_preview_with_array_content(self):
        """Test extract_user_input_preview with array content."""
        messages = json.dumps([
            {"role": "user", "content": [
                {"type": "text", "text": "Help me with this"}
            ]}
        ])
        result = extract_user_input_preview(messages)
        assert "Help me with this" in result

    def test_extract_user_input_preview_empty(self):
        """Test extract_user_input_preview with empty messages."""
        result = extract_user_input_preview(json.dumps([]))
        assert result == "No user input"

    def test_extract_user_input_preview_truncate(self):
        """Test that long content is truncated."""
        long_text = "A" * 300
        messages = json.dumps([
            {"role": "user", "content": long_text}
        ])
        result = extract_user_input_preview(messages, max_length=200)
        assert len(result) <= 203  # 200 + "..."
        assert result.endswith("...")

    def test_extract_user_input_preview_invalid_json(self):
        """Test extract_user_input_preview with invalid JSON."""
        result = extract_user_input_preview("invalid json")
        assert result == "Error parsing input"


# =============================================================================
# Page Route Tests
# =============================================================================

class TestPageRoutes:
    """Test page rendering routes."""

    def test_index_page(self, client):
        """Test index page loads."""
        response = client.get('/')
        assert response.status_code == 200

    def test_sessions_page(self, client):
        """Test sessions page loads."""
        response = client.get('/sessions')
        assert response.status_code == 200

    def test_session_detail_page(self, client):
        """Test session detail page loads."""
        response = client.get('/sessions/sess_test123')
        assert response.status_code == 200

    def test_request_detail_page(self, client):
        """Test request detail page loads."""
        response = client.get('/requests/req_test456')
        assert response.status_code == 200

    def test_analysis_page(self, client):
        """Test analysis page loads."""
        response = client.get('/analysis')
        assert response.status_code == 200


# =============================================================================
# Statistics API Tests
# =============================================================================

class TestStatisticsAPI:
    """Test statistics API endpoints."""

    @patch('web.app.stats_engine')
    def test_statistics_summary(self, mock_engine, client):
        """Test statistics summary endpoint."""
        # Mock the summary response
        mock_summary = Mock()
        mock_summary.total_requests = 100
        mock_summary.total_sessions = 10
        mock_summary.total_input_tokens = 50000
        mock_summary.total_output_tokens = 20000
        mock_summary.cache_creation_tokens = 1000
        mock_summary.cache_read_tokens = 2000
        mock_summary.total_cost = 5.0
        mock_summary.avg_response_time_ms = 1500
        mock_summary.requests_today = 20
        mock_summary.cost_today = 1.0
        mock_engine.get_summary.return_value = mock_summary

        response = client.get('/api/statistics/summary')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['total_requests'] == 100
        assert data['total_sessions'] == 10
        assert data['total_cost'] == 5.0

    @patch('web.app.stats_engine')
    def test_statistics_summary_with_hours_filter(self, mock_engine, client):
        """Test statistics summary with hours filter."""
        from analysis.statistics import SummaryStats
        mock_summary = SummaryStats(
            total_requests=50,
            total_sessions=5,
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cost=0.5,
            avg_response_time_ms=1000,
            requests_today=10,
            cost_today=0.1
        )
        mock_engine.get_summary.return_value = mock_summary

        response = client.get('/api/statistics/summary?hours=24')
        assert response.status_code == 200

        # Verify hours parameter was passed
        mock_engine.get_summary.assert_called_once_with(hours=24)

    @patch('web.app.stats_engine')
    def test_statistics_timeline(self, mock_engine, client):
        """Test statistics timeline endpoint."""
        mock_engine.get_request_volume_timeline.return_value = [
            {"timestamp": "2024-03-28T10:00:00", "count": 10},
            {"timestamp": "2024-03-28T11:00:00", "count": 20}
        ]

        response = client.get('/api/statistics/timeline')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]['count'] == 10

    @patch('web.app.stats_engine')
    def test_statistics_models(self, mock_engine, client):
        """Test statistics models endpoint."""
        mock_engine.get_model_distribution.return_value = {
            "claude-3-opus": {"requests": 50, "tokens": 10000},
            "claude-3-sonnet": {"requests": 30, "tokens": 6000}
        }

        response = client.get('/api/statistics/models')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "claude-3-opus" in data

    @patch('web.app.tool_analyzer')
    def test_statistics_tools(self, mock_analyzer, client):
        """Test statistics tools endpoint."""
        # Create simple objects with attributes for API access
        class ToolStat:
            def __init__(self, name, calls, duration):
                self.name = name
                self.total_calls = calls
                self.avg_duration_ms = duration

        mock_tool_stats = [
            ToolStat("Glob", 50, 100),
            ToolStat("Read", 30, 50)
        ]
        mock_analyzer.get_tool_usage_stats.return_value = mock_tool_stats

        response = client.get('/api/statistics/tools')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data) == 2
        assert data[0]['name'] == "Glob"
        assert data[0]['calls'] == 50


# =============================================================================
# Sessions API Tests
# =============================================================================

class TestSessionsAPI:
    """Test sessions API endpoints."""

    @patch('web.app.db')
    def test_get_sessions_list(self, mock_db, client):
        """Test getting list of sessions."""
        mock_sessions = [
            Session(
                id=1,
                session_id="sess_1",
                started_at=datetime.now(),
                total_requests=10,
                total_cost=1.0
            ),
            Session(
                id=2,
                session_id="sess_2",
                started_at=datetime.now(),
                total_requests=20,
                total_cost=2.0
            )
        ]
        mock_db.get_sessions.return_value = (mock_sessions, 2)

        response = client.get('/api/sessions')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert len(data['sessions']) == 2
        assert data['total'] == 2
        assert data['page'] == 1

    @patch('web.app.db')
    def test_get_sessions_with_filters(self, mock_db, client):
        """Test getting sessions with filters."""
        mock_db.get_sessions.return_value = ([], 0)

        response = client.get('/api/sessions?session_id=sess_1&model=opus&date_from=2024-01-01&date_to=2024-12-31')
        assert response.status_code == 200

        # Verify filters were passed to db
        call_kwargs = mock_db.get_sessions.call_args[1]
        assert call_kwargs['session_id_filter'] == 'sess_1'
        assert call_kwargs['model_filter'] == 'opus'
        assert call_kwargs['date_from'] == '2024-01-01'
        assert call_kwargs['date_to'] == '2024-12-31'

    @patch('web.app.db')
    def test_get_session_detail_success(self, mock_db, client, mock_session, mock_request):
        """Test getting session detail with requests."""
        mock_db.get_session.return_value = mock_session
        mock_db.get_requests_by_session.return_value = [mock_request]
        mock_db.get_request_count_by_session.return_value = 1
        mock_db.get_tool_calls_by_request.return_value = []

        response = client.get('/api/sessions/sess_test123')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['session']['session_id'] == 'sess_test123'
        assert len(data['requests']) == 1
        assert data['requests'][0]['request_id'] == 'req_test456'

    @patch('web.app.db')
    def test_get_session_detail_not_found(self, mock_db, client):
        """Test getting non-existent session."""
        mock_db.get_session.return_value = None

        response = client.get('/api/sessions/nonexistent')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data

    @patch('web.app.db')
    def test_get_session_detail_with_pagination(self, mock_db, client, mock_session, mock_request):
        """Test session detail with pagination."""
        mock_db.get_session.return_value = mock_session
        mock_db.get_requests_by_session.return_value = [mock_request]
        mock_db.get_request_count_by_session.return_value = 100
        mock_db.get_tool_calls_by_request.return_value = []

        response = client.get('/api/sessions/sess_test123?page=2&per_page=10')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['pagination']['page'] == 2
        assert data['pagination']['per_page'] == 10
        assert data['pagination']['total_pages'] == 10


# =============================================================================
# Requests API Tests
# =============================================================================

class TestRequestsAPI:
    """Test requests API endpoints."""

    @patch('web.app.db')
    def test_get_request_detail_success(self, mock_db, client, mock_request, mock_tool_call):
        """Test getting request detail."""
        mock_db.get_request.return_value = mock_request
        mock_db.get_tool_calls_by_request.return_value = [mock_tool_call]

        response = client.get('/api/requests/req_test456')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['request']['request_id'] == 'req_test456'
        assert data['request']['response_text'] == "I'm doing well, thank you!"
        assert len(data['tool_calls']) == 1
        assert data['tool_calls'][0]['tool_name'] == 'Glob'

    @patch('web.app.db')
    def test_get_request_detail_not_found(self, mock_db, client):
        """Test getting non-existent request."""
        mock_db.get_request.return_value = None

        response = client.get('/api/requests/nonexistent')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data

    @patch('web.app.db')
    def test_get_request_includes_user_input_preview(self, mock_db, client, mock_request):
        """Test that request detail includes user_input_preview."""
        mock_db.get_request.return_value = mock_request
        mock_db.get_tool_calls_by_request.return_value = []

        response = client.get('/api/requests/req_test456')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'user_input_preview' in data['request']


# =============================================================================
# Analysis API Tests
# =============================================================================

class TestAnalysisAPI:
    """Test analysis API endpoints."""

    @patch('web.app.token_analyzer')
    def test_analysis_tokens(self, mock_analyzer, client):
        """Test token analysis endpoint."""
        # Mock overall usage
        mock_usage = Mock(input_tokens=10000, output_tokens=5000, total_tokens=15000, cost=1.5)
        mock_analyzer.get_overall_usage.return_value = mock_usage

        # Mock by model
        mock_model_usage = Mock(input_tokens=8000, output_tokens=4000, total_tokens=12000, cost=1.2)
        mock_analyzer.get_usage_by_model.return_value = {
            "claude-3-opus": mock_model_usage
        }

        # Mock efficiency
        mock_analyzer.get_efficiency_metrics.return_value = {"cache_hit_rate": 0.3}

        # Mock monthly estimate
        mock_analyzer.estimate_monthly_cost.return_value = {"estimated_cost": 45.0}

        response = client.get('/api/analysis/tokens')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'overall' in data
        assert 'by_model' in data
        assert 'efficiency' in data
        assert 'monthly_estimate' in data
        assert data['overall']['cost'] == 1.5

    @patch('web.app.tool_analyzer')
    def test_analysis_tools(self, mock_analyzer, client):
        """Test tool analysis endpoint."""
        mock_analyzer.get_tool_usage_distribution.return_value = {"Glob": 50, "Read": 30}
        mock_analyzer.get_tool_category_distribution.return_value = {"file": 80}
        mock_analyzer.get_most_used_tools.return_value = ["Glob", "Read"]
        mock_analyzer.get_slowest_tools.return_value = ["Glob"]
        mock_analyzer.analyze_tool_patterns.return_value = {"sequential_usage": 0.8}

        response = client.get('/api/analysis/tools')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'distribution' in data
        assert 'categories' in data
        assert 'most_used' in data
        assert 'slowest' in data
        assert 'patterns' in data


# =============================================================================
# Export API Tests
# =============================================================================

class TestExportAPI:
    """Test export API endpoints."""

    @patch('web.app.db')
    def test_export_sessions_json(self, mock_db, client):
        """Test exporting sessions in JSON format."""
        # Return plain dicts instead of Mock objects for JSON serialization
        mock_sessions = [
            {"id": 1, "session_id": "sess_1", "total_requests": 10},
            {"id": 2, "session_id": "sess_2", "total_requests": 20}
        ]
        mock_db.get_sessions.return_value = mock_sessions

        response = client.get('/api/export/sessions?format=json')
        assert response.status_code == 200

    @patch('web.app.db')
    def test_export_sessions_unsupported_format(self, mock_db, client):
        """Test exporting sessions in unsupported format."""
        response = client.get('/api/export/sessions?format=csv')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert 'error' in data

    @patch('web.app.db')
    def test_export_single_session_success(self, mock_db, client, mock_session, mock_request):
        """Test exporting single session."""
        mock_db.get_session.return_value = mock_session
        mock_db.get_requests_by_session.return_value = [mock_request]

        response = client.get('/api/export/session/sess_test123')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert 'session' in data
        assert 'requests' in data

    @patch('web.app.db')
    def test_export_single_session_not_found(self, mock_db, client):
        """Test exporting non-existent session."""
        mock_db.get_session.return_value = None

        response = client.get('/api/export/session/nonexistent')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert 'error' in data


# =============================================================================
# Error Handler Tests
# =============================================================================

class TestErrorHandlers:
    """Test error handlers."""

    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get('/nonexistent-route')
        assert response.status_code == 404

    def test_404_json_error(self, client):
        """Test 404 JSON error for API routes."""
        # API routes should return JSON
        response = client.get('/api/nonexistent',
                              headers={'Accept': 'application/json'})
        assert response.status_code == 404


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests covering multiple endpoints."""

    @patch('web.app.db')
    @patch('web.app.stats_engine')
    @patch('web.app.token_analyzer')
    def test_full_workflow(self, mock_token_analyzer, mock_stats_engine, mock_db, client):
        """Test a full workflow: sessions -> session detail -> request detail."""
        # Create mock session
        mock_session = Session(
            id=1,
            session_id="sess_workflow",
            started_at=datetime.now(),
            total_requests=1,
            total_cost=0.1
        )

        # Create mock request
        mock_request = Request(
            id=1,
            request_id="req_workflow",
            session_id="sess_workflow",
            timestamp=datetime.now(),
            model="claude-3-opus",
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            messages_json=json.dumps([{"role": "user", "content": "Test"}]),
            response_text="Test response"
        )

        # Setup mocks
        mock_db.get_sessions.return_value = ([mock_session], 1)
        mock_db.get_session.return_value = mock_session
        mock_db.get_requests_by_session.return_value = [mock_request]
        mock_db.get_request_count_by_session.return_value = 1
        mock_db.get_request.return_value = mock_request
        mock_db.get_tool_calls_by_request.return_value = []

        # Step 1: Get sessions list
        response = client.get('/api/sessions')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['sessions']) == 1
        session_id = data['sessions'][0]['session_id']

        # Step 2: Get session detail
        response = client.get(f'/api/sessions/{session_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['session']['session_id'] == session_id
        assert len(data['requests']) == 1
        request_id = data['requests'][0]['request_id']

        # Step 3: Get request detail
        response = client.get(f'/api/requests/{request_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['request']['request_id'] == request_id


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
