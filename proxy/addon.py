"""
MITM Proxy Addon for capturing Claude Code API interactions.

This is the main entry point for the proxy server. It intercepts
HTTP(S) requests and responses, filters for Anthropic API calls,
and stores them for analysis.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from mitmproxy import http, ctx
from mitmproxy.http import Headers

from config.settings import TARGET_DOMAINS, DATABASE_PATH
from proxy.anthropic_handler import AnthropicHandler, APIInteraction
from storage.database import Database
from storage.models import Session, Request, ToolCall, Message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CaptureState:
    """State tracking for the capture addon."""

    def __init__(self):
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, Session] = {}


class AnthropicCaptureAddon:
    """
    MITM Proxy addon for capturing Anthropic API interactions.

    Intercepts all HTTP(S) traffic, filters for Anthropic API calls,
    parses requests and responses, and stores them in SQLite.
    """

    def __init__(self):
        self.state = CaptureState()
        self.handler = AnthropicHandler()
        self.db: Optional[Database] = None

    def load(self, loader):
        """Called when the addon is loaded."""
        logger.info("Loading AnthropicCaptureAddon...")

        # Initialize database
        self.db = Database(DATABASE_PATH)
        logger.info(f"Database initialized at {DATABASE_PATH}")

    def request(self, flow: http.HTTPFlow) -> None:
        """
        Handle an incoming request.

        Args:
            flow: The HTTP flow containing the request
        """
        host = flow.request.pretty_host.lower()
        path = flow.request.path
        method = flow.request.method

        # Log all HTTPS requests for debugging
        if flow.request.scheme == "https":
            logger.info(f"[REQUEST] {method} https://{host}{path}")

        # Capture ALL POST requests to messages-like endpoints
        is_messages_api = "/v1/messages" in path or "/messages" in path
        is_post = method == "POST"

        # Check if this looks like an API request
        if is_post and is_messages_api:
            flow.metadata["is_tracked"] = True
            flow.metadata["start_time"] = datetime.now()

            # Parse request
            try:
                body_content = flow.request.content
                logger.info(f"Request body size: {len(body_content)} bytes")

                parsed = self.handler.parse_request(
                    method=flow.request.method,
                    endpoint=flow.request.path,
                    headers=dict(flow.request.headers),
                    body=body_content,
                )

                if parsed:
                    flow.metadata["parsed_request"] = parsed
                    logger.info(f"Parsed request: {parsed.request_id} to model={parsed.model}")

                    # Track session
                    self._update_session(parsed)

            except Exception as e:
                logger.error(f"Error parsing request: {e}")

    def response(self, flow: http.HTTPFlow) -> None:
        """
        Handle an outgoing response.

        Args:
            flow: The HTTP flow containing the response
        """
        # Only process tracked requests
        if not flow.metadata.get("is_tracked"):
            return

        parsed_request = flow.metadata.get("parsed_request")
        if not parsed_request:
            return

        # Calculate response time
        start_time = flow.metadata.get("start_time", datetime.now())
        response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Handle streaming vs non-streaming
        is_streaming = self._is_streaming_response(flow)

        try:
            if is_streaming:
                # Streaming response - parse SSE events
                response_body = flow.response.content

                # Parse the streaming response using SSEParser
                from proxy.stream_parser import SSEParser
                parser = SSEParser()
                parser.feed(response_body)
                parsed_response = parser.get_response()

                interaction = self.handler.create_interaction(
                    parsed_request=parsed_request,
                    response_status=flow.response.status_code,
                    response_time_ms=response_time_ms,
                    response_body=response_body,
                )

                # Override with parsed streaming data
                if parsed_response:
                    interaction.parsed_response = parsed_response
                    interaction.input_tokens = parsed_response.input_tokens
                    interaction.output_tokens = parsed_response.output_tokens
                    interaction.cache_creation_tokens = parsed_response.cache_creation_tokens
                    interaction.cache_read_tokens = parsed_response.cache_read_tokens
                    interaction.calculate_cost()

                # Store the interaction
                self._store_interaction(interaction)

                logger.info(
                    f"Captured streaming request: {interaction.request_id}, "
                    f"tokens: {interaction.input_tokens}/{interaction.output_tokens}, "
                    f"cost: ${interaction.cost:.4f}"
                )
            else:
                # Non-streaming response
                interaction = self.handler.create_interaction(
                    parsed_request=parsed_request,
                    response_status=flow.response.status_code,
                    response_time_ms=response_time_ms,
                    response_body=flow.response.content,
                )

                # Store the interaction
                self._store_interaction(interaction)

                logger.info(
                    f"Captured request: {interaction.request_id}, "
                    f"tokens: {interaction.input_tokens}/{interaction.output_tokens}, "
                    f"cost: ${interaction.cost:.4f}"
                )

        except Exception as e:
            logger.error(f"Error processing response: {e}")

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        """
        Handle response headers (called before response body).

        This is where we detect streaming responses.

        Args:
            flow: The HTTP flow
        """
        if not flow.metadata.get("is_tracked"):
            return

        if self._is_streaming_response(flow):
            # Initialize streaming state
            flow.metadata["streaming"] = True
            flow.metadata["chunks"] = []

    def error(self, flow: http.HTTPFlow) -> None:
        """
        Handle an error - store the request even if response failed.

        Args:
            flow: The HTTP flow with error
        """
        logger.error(f"Flow error: {flow.error}")

        # Only process tracked requests
        if not flow.metadata.get("is_tracked"):
            return

        parsed_request = flow.metadata.get("parsed_request")
        if not parsed_request:
            return

        try:
            # Calculate response time up to error
            start_time = flow.metadata.get("start_time", datetime.now())
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Check if we have partial response data
            response_body = b""
            response_status = 0
            if flow.response:
                response_body = flow.response.content or b""
                response_status = flow.response.status_code

            # Create interaction
            interaction = self.handler.create_interaction(
                parsed_request=parsed_request,
                response_status=response_status,
                response_time_ms=response_time_ms,
                response_body=response_body,
            )

            # Mark as having an error
            if interaction.response_body:
                interaction.response_body += f"\n[ERROR: {flow.error}]"
            else:
                interaction.response_body = f"[ERROR: {flow.error}]"

            # Store the interaction
            self._store_interaction(interaction)

            logger.info(
                f"Captured request (with error): {interaction.request_id}, "
                f"error: {flow.error}"
            )

        except Exception as e:
            logger.error(f"Error storing failed request: {e}")

    def _is_target_request(self, flow: http.HTTPFlow) -> bool:
        """Check if this is a target API request."""
        host = flow.request.pretty_host.lower()

        for target in TARGET_DOMAINS:
            if target.lower() in host:
                return True

        return False

    def _is_streaming_response(self, flow: http.HTTPFlow) -> bool:
        """Check if this is a streaming response."""
        if not flow.response:
            return False

        content_type = flow.response.headers.get("content-type", "").lower()

        # Check for SSE or streaming JSON
        if "text/event-stream" in content_type:
            return True
        if "application/stream+json" in content_type:
            return True

        # Also check request for streaming flag
        parsed_request = flow.metadata.get("parsed_request")
        if parsed_request and parsed_request.is_streaming:
            return True

        return False

    def _update_session(self, parsed_request) -> None:
        """Update or create a session."""
        session_id = parsed_request.session_id
        logger.info(f"[_update_session] session_id={session_id}, active_sessions={list(self.state.active_sessions.keys())}")

        if session_id not in self.state.active_sessions:
            # Try to load existing session from database
            existing_session = self.db.get_session(session_id)
            logger.info(f"[_update_session] Loaded from DB: {existing_session is not None}")
            if existing_session:
                # Restore session from database
                self.state.active_sessions[session_id] = existing_session
                logger.info(f"[_update_session] Restored session from DB: total_requests={existing_session.total_requests}")
            else:
                # Create new session
                session = Session(
                    session_id=session_id,
                    started_at=datetime.now(),
                    user_agent=parsed_request.user_agent,
                    working_directory=parsed_request.working_directory,
                    model=parsed_request.model,
                )
                self.state.active_sessions[session_id] = session

                # Save to database
                self.db.upsert_session(session)
        else:
            # Update existing session
            session = self.state.active_sessions[session_id]
            session.model = parsed_request.model

    def _store_interaction(self, interaction: APIInteraction) -> None:
        """Store an API interaction in the database."""
        if not self.db:
            logger.warning("Database not initialized")
            return

        # Filter out dirty data: Haiku model with zero tokens
        model = interaction.parsed_request.model or ""
        total_tokens = interaction.input_tokens + interaction.output_tokens
        if "haiku" in model.lower() and total_tokens == 0:
            logger.info(f"Skipping dirty data: {interaction.request_id} (Haiku with 0 tokens)")
            return

        # Update session
        session_id = interaction.parsed_request.session_id
        logger.info(f"[_store_interaction] session_id={session_id}, in_active={session_id in self.state.active_sessions}")
        if session_id in self.state.active_sessions:
            session = self.state.active_sessions[session_id]
            session.total_requests += 1
            session.total_input_tokens += interaction.input_tokens
            session.total_output_tokens += interaction.output_tokens
            session.total_cost += interaction.cost
            session.ended_at = datetime.now()
            self.db.upsert_session(session)
            logger.info(f"[_store_interaction] Updated session: total_requests={session.total_requests}")

        # Extract parsed response content
        response_text = ""
        response_thinking = ""
        if interaction.parsed_response:
            response_text = interaction.parsed_response.text_content
            response_thinking = interaction.parsed_response.thinking_content

        # Create request record (without streaming response body to save space)
        request = Request(
            request_id=interaction.request_id,
            session_id=session_id,
            timestamp=interaction.timestamp,
            method="POST",
            endpoint="/v1/messages",
            model=interaction.parsed_request.model,
            system_prompt=interaction.parsed_request.system_prompt,
            messages_json=json.dumps(interaction.parsed_request.messages),
            response_status=interaction.response_status,
            response_time_ms=interaction.response_time_ms,
            is_streaming=interaction.parsed_request.is_streaming,
            input_tokens=interaction.input_tokens,
            output_tokens=interaction.output_tokens,
            cache_creation_tokens=interaction.cache_creation_tokens,
            cache_read_tokens=interaction.cache_read_tokens,
            cost=interaction.cost,
            request_body=interaction.request_body,
            response_body="",  # Skip streaming response body to save space
            response_text=response_text,
            response_thinking=response_thinking,
        )

        self.db.save_request(request)

        # Store tool calls if present
        if interaction.parsed_response:
            tool_uses = interaction.parsed_response.get_tool_uses()
            for tool_use in tool_uses:
                tool_call = ToolCall(
                    request_id=interaction.request_id,
                    tool_name=tool_use.get("name", ""),
                    tool_input_json=json.dumps(tool_use.get("input", {})),
                )
                self.db.save_tool_call(tool_call)


# Export addon for mitmproxy
addons = [AnthropicCaptureAddon()]