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

from config.settings import TARGET_DOMAINS, DATABASE_PATH, DATA_CLEANUP_ENABLED, WEB_HOST, WEB_PORT
from proxy.anthropic_handler import AnthropicHandler, APIInteraction
from proxy.filter_engine import URLFilterEngine
from proxy.log_manager import init_log_manager, get_log_manager
from storage.database import Database
from storage.models import Session, Request, ToolCall, Message
from storage.worker import init_worker, enqueue_write, shutdown_worker, get_worker
from storage.cleanup import DataCleanupManager, CleanupScheduler
from storage.recycle_bin import RecycleBinManager, CleanupLogManager, SettingsManager

# SocketIO client for real-time WebSocket broadcast
import socketio

# Configure logging - runtime logger will be used via log_manager
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
log_manager = None  # Will be initialized in load()


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
        self.filter_engine: Optional[URLFilterEngine] = None
        self.cleanup_manager: Optional[DataCleanupManager] = None
        self.cleanup_scheduler: Optional[CleanupScheduler] = None
        self.recycle_bin: Optional[RecycleBinManager] = None
        self.log_manager: Optional[CleanupLogManager] = None
        self.settings_manager: Optional[SettingsManager] = None
        self._socketio_client: Optional[socketio.SimpleClient] = None

    def load(self, loader):
        """Called when the addon is loaded."""
        logger.info("Loading AnthropicCaptureAddon...")

        # Initialize log manager for rotating log files
        log_manager = init_log_manager()
        log_manager.log_info("Loading AnthropicCaptureAddon...")
        logger.info(f"Log manager initialized, logs stored in {log_manager.log_dir}")

        # Initialize database
        self.db = Database(DATABASE_PATH)
        logger.info(f"Database initialized at {DATABASE_PATH}")
        log_manager.log_info(f"Database initialized at {DATABASE_PATH}")

        # Initialize settings manager for dynamic configuration
        try:
            self.settings_manager = SettingsManager(self.db)
            logger.info("Settings manager initialized")
            log_manager.log_info("Settings manager initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize settings manager: {e}")
            self.settings_manager = None

        # Initialize URL filter engine
        self.filter_engine = URLFilterEngine(self.db)
        logger.info("URL filter engine initialized")
        log_manager.log_info("URL filter engine initialized")

        # Initialize background write worker
        init_worker(self.db, batch_size=10, batch_interval=0.1)
        logger.info("Background write worker initialized")
        log_manager.log_info("Background write worker initialized")

        # Initialize SocketIO client for real-time broadcast
        self._socketio_client: Optional[socketio.SimpleClient] = None
        self._init_socketio_client()

        # Initialize data cleanup with recycle bin support (if enabled)
        if DATA_CLEANUP_ENABLED:
            try:
                # Check if recycle bin is enabled
                use_recycle_bin = True
                if self.settings_manager:
                    use_recycle_bin = self.settings_manager.get_setting('recycle_bin_enabled', True)

                if use_recycle_bin:
                    # Initialize recycle bin manager
                    recycle_bin_days = 7
                    if self.settings_manager:
                        recycle_bin_days = self.settings_manager.get_setting('recycle_bin_retention_days', 7)
                    self.recycle_bin = RecycleBinManager(self.db, retention_days=recycle_bin_days)
                    logger.info(f"Recycle bin manager initialized ({recycle_bin_days} days retention)")
                    log_manager.log_info(f"Recycle bin manager initialized ({recycle_bin_days} days retention)")

                    # Initialize log manager
                    self.log_manager = CleanupLogManager(self.db)
                    logger.info("Cleanup log manager initialized")
                    log_manager.log_info("Cleanup log manager initialized")

                # Initialize cleanup manager with recycle bin support
                self.cleanup_manager = DataCleanupManager(
                    self.db,
                    recycle_bin=self.recycle_bin,
                    log_manager=self.log_manager,
                    use_recycle_bin=use_recycle_bin
                )

                # Initialize cleanup scheduler
                self.cleanup_scheduler = CleanupScheduler(
                    self.db,
                    cleanup_manager=self.cleanup_manager,
                    recycle_bin=self.recycle_bin,
                    log_manager=self.log_manager,
                    settings_manager=self.settings_manager
                )
                self.cleanup_scheduler.start()
                logger.info("Data cleanup scheduler initialized")
                log_manager.log_info("Data cleanup scheduler initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize cleanup scheduler: {e}")
                log_manager.log_warning(f"Failed to initialize cleanup scheduler: {e}")

    def _init_socketio_client(self):
        """
        Initialize SocketIO client for real-time broadcast with retry.

        Starts a background thread to connect to the web server's SocketIO
        endpoint, retrying with exponential backoff until successful.
        """
        import threading
        import time

        def connect_with_retry():
            max_retries = 30  # Try for about 5 minutes
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    client = socketio.SimpleClient()
                    socketio_url = f"http://{WEB_HOST}:{WEB_PORT}"
                    client.connect(socketio_url)
                    self._socketio_client = client
                    logger.info(f"SocketIO client connected to {socketio_url} (attempt {attempt + 1})")
                    log_manager.log_info(f"SocketIO client connected to {socketio_url} (attempt {attempt + 1})")

                    # Set up write worker callback
                    worker = get_worker()
                    if worker:
                        worker.on_write_callback = lambda req: self._broadcast_request(req.to_dict())
                        logger.info("Write worker callback configured for SocketIO broadcast")
                        log_manager.log_info("Write worker callback configured for SocketIO broadcast")
                    return
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.debug(f"SocketIO connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                    else:
                        logger.warning(f"Failed to connect SocketIO client after {max_retries} attempts: {e}. Real-time updates disabled.")
                        log_manager.log_warning(f"Failed to connect SocketIO client after {max_retries} attempts: {e}. Real-time updates disabled.")

        # Start connection in background thread
        threading.Thread(target=connect_with_retry, daemon=True, name="SocketIOClient").start()

    def _broadcast_request(self, request_data: Dict[str, Any]):
        """
        Broadcast a new request to connected clients via SocketIO.

        Sends to server's proxy_broadcast handler which then broadcasts
        to all subscribed clients.

        Args:
            request_data: Dict with request information
        """
        if self._socketio_client and self._socketio_client.connected:
            try:
                self._socketio_client.emit('proxy_broadcast', {
                    'event': 'new_request',
                    'data': request_data,
                    'room': 'requests'
                })
                logger.debug(f"Broadcasted new_request via proxy: {request_data.get('request_id', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to broadcast request: {e}")

    def request(self, flow: http.HTTPFlow) -> None:
        """
        Handle an incoming request.

        Args:
            flow: The HTTP flow containing the request
        """
        host = flow.request.pretty_host.lower()
        path = flow.request.path
        method = flow.request.method
        url = f"{flow.request.scheme}://{host}{path}"

        # Log all HTTPS requests for debugging
        if flow.request.scheme == "https":
            logger.info(f"[REQUEST] {method} {url}")
            # Also log to rotating file
            log_manager = get_log_manager()
            if log_manager:
                log_manager.log_debug(f"[REQUEST] {method} {url}")

        # Check if URL should be captured based on filter rules
        if not self.filter_engine or not self.filter_engine.should_capture(url):
            return

        # Only capture POST requests to messages-like endpoints
        is_messages_api = "/v1/messages" in path or "/messages" in path
        is_post = method == "POST"

        if not (is_post and is_messages_api):
            return

        # Mark as tracked and capture
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
                # Also log to rotating file
                log_manager = get_log_manager()
                if log_manager:
                    log_manager.log_info(f"Parsed request: {parsed.request_id} to model={parsed.model}")

                # Track session
                self._update_session(parsed)

        except Exception as e:
            logger.error(f"Error parsing request: {e}")
            log_manager = get_log_manager()
            if log_manager:
                log_manager.log_error(f"Error parsing request: {e}")

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
            # Convert response headers to dict
            response_headers = dict(flow.response.headers) if flow.response else {}

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
                    response_headers=response_headers,
                )

                # Override with parsed streaming data
                if parsed_response:
                    interaction.parsed_response = parsed_response
                    interaction.input_tokens = parsed_response.input_tokens
                    interaction.output_tokens = parsed_response.output_tokens
                    interaction.cache_creation_tokens = parsed_response.cache_creation_tokens
                    interaction.cache_read_tokens = parsed_response.cache_read_tokens
                    interaction.calculate_cost()

                # Store the interaction with timing info and streaming metrics
                self._store_interaction(interaction, flow, parsed_response)

                logger.info(
                    f"Captured streaming request: {interaction.request_id}, "
                    f"tokens: {interaction.input_tokens}/{interaction.output_tokens}, "
                    f"cost: ${interaction.cost:.4f}"
                )
                # Also log to rotating file
                log_manager = get_log_manager()
                if log_manager:
                    log_manager.log_info(
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
                    response_headers=response_headers,
                )

                # Store the interaction with timing info (no streaming metrics for non-streaming)
                self._store_interaction(interaction, flow, None)

                logger.info(
                    f"Captured request: {interaction.request_id}, "
                    f"tokens: {interaction.input_tokens}/{interaction.output_tokens}, "
                    f"cost: ${interaction.cost:.4f}"
                )
                # Also log to rotating file
                log_manager = get_log_manager()
                if log_manager:
                    log_manager.log_info(
                        f"Captured request: {interaction.request_id}, "
                        f"tokens: {interaction.input_tokens}/{interaction.output_tokens}, "
                        f"cost: ${interaction.cost:.4f}"
                    )

        except Exception as e:
            logger.error(f"Error processing response: {e}")
            log_manager = get_log_manager()
            if log_manager:
                log_manager.log_error(f"Error processing response: {e}")

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
        log_manager = get_log_manager()
        if log_manager:
            log_manager.log_error(f"Flow error: {flow.error}")

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

            # Store the interaction with flow for timing info (no streaming on error)
            self._store_interaction(interaction, flow, None)

            logger.info(
                f"Captured request (with error): {interaction.request_id}, "
                f"error: {flow.error}"
            )
            if log_manager:
                log_manager.log_info(
                    f"Captured request (with error): {interaction.request_id}, "
                    f"error: {flow.error}"
                )

        except Exception as e:
            logger.error(f"Error storing failed request: {e}")
            if log_manager:
                log_manager.log_error(f"Error storing failed request: {e}")

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

    def _extract_timing_info(self, flow: http.HTTPFlow) -> Dict[str, int]:
        """
        Extract detailed timing from HTTP flow.

        Uses mitmproxy's built-in timestamps to calculate phase timings.
        """
        timing = {}

        # Server connection timing (TCP connect)
        if (flow.server_conn.timestamp_start and flow.server_conn.timestamp_tcp_setup):
            timing['connect_ms'] = int(
                (flow.server_conn.timestamp_tcp_setup - flow.server_conn.timestamp_start) * 1000
            )

        # TLS handshake timing
        if (flow.server_conn.timestamp_tcp_setup and flow.server_conn.timestamp_tls_setup):
            timing['tls_ms'] = int(
                (flow.server_conn.timestamp_tls_setup - flow.server_conn.timestamp_tcp_setup) * 1000
            )

        # Request timing - time to send the request
        if flow.request.timestamp_start and flow.request.timestamp_end:
            timing['send_ms'] = int(
                (flow.request.timestamp_end - flow.request.timestamp_start) * 1000
            )

        # Time to first byte (server processing + network latency)
        if (flow.response and flow.request.timestamp_end and flow.response.timestamp_start):
            timing['wait_ms'] = int(
                (flow.response.timestamp_start - flow.request.timestamp_end) * 1000
            )

        # Response receive time
        if flow.response and flow.response.timestamp_start and flow.response.timestamp_end:
            timing['receive_ms'] = int(
                (flow.response.timestamp_end - flow.response.timestamp_start) * 1000
            )

        return timing

    def _calc_time_to_first_token(self, wait_ms: Optional[int], parsed_response) -> Optional[int]:
        """Calculate time to first token (wait time + first token generation)."""
        if not parsed_response or not parsed_response.first_token_time:
            return None
        # Time to first token = wait_ms (time to first byte) + any additional time
        # For simplicity, we estimate based on first token arrival
        return wait_ms if wait_ms else 0

    def _calc_time_to_last_token(self, wait_ms: Optional[int], parsed_response) -> Optional[int]:
        """Calculate time to last token."""
        if not parsed_response or not parsed_response.first_token_time or not parsed_response.last_token_time:
            return None
        # Total generation time from first to last token
        return parsed_response.total_generation_ms

    def _calc_avg_token_latency(self, parsed_response) -> Optional[int]:
        """Calculate average time between tokens."""
        if not parsed_response or parsed_response.token_count < 2:
            return None
        # Average time per token = total generation time / (token count - 1)
        # (subtract 1 because latency is between tokens)
        return parsed_response.total_generation_ms // (parsed_response.token_count - 1)

    def _update_session(self, parsed_request) -> None:
        """Update or create a session."""
        session_id = parsed_request.session_id
        logger.info(f"[_update_session] session_id={session_id}, active_sessions={list(self.state.active_sessions.keys())}")
        log_manager = get_log_manager()
        if log_manager:
            log_manager.log_debug(f"[_update_session] session_id={session_id}, active_sessions={list(self.state.active_sessions.keys())}")

        if session_id not in self.state.active_sessions:
            # Try to load existing session from database
            existing_session = self.db.get_session(session_id)
            logger.info(f"[_update_session] Loaded from DB: {existing_session is not None}")
            if log_manager:
                log_manager.log_debug(f"[_update_session] Loaded from DB: {existing_session is not None}")
            if existing_session:
                # Restore session from database
                self.state.active_sessions[session_id] = existing_session
                logger.info(f"[_update_session] Restored session from DB: total_requests={existing_session.total_requests}")
                if log_manager:
                    log_manager.log_debug(f"[_update_session] Restored session from DB: total_requests={existing_session.total_requests}")
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

    def _store_interaction(self, interaction: APIInteraction, flow: http.HTTPFlow = None, parsed_response=None) -> None:
        """Store an API interaction in the database and log request details."""
        if not self.db:
            logger.warning("Database not initialized")
            return

        # Log request details to separate log file
        log_manager = get_log_manager()
        if log_manager:
            # Get URL from flow if available, otherwise use placeholder
            if flow:
                url = flow.request.url
            else:
                url = f"https://api.anthropic.com/v1/messages"
            extra_data = {
                'request_id': interaction.request_id,
                'model': interaction.parsed_request.model,
                'input_tokens': interaction.input_tokens,
                'output_tokens': interaction.output_tokens,
                'cost': interaction.cost,
                'response_time_ms': interaction.response_time_ms,
            }
            log_manager.log_request(
                url=url,
                request_body=interaction.request_body,
                response_body=interaction.response_body or '',
                extra_data=extra_data
            )

        # Filter out dirty data: Haiku model with zero tokens
        model = interaction.parsed_request.model or ""
        total_tokens = interaction.input_tokens + interaction.output_tokens
        if "haiku" in model.lower() and total_tokens == 0:
            logger.info(f"Skipping dirty data: {interaction.request_id} (Haiku with 0 tokens)")
            log_manager.log_info(f"Skipping dirty data: {interaction.request_id} (Haiku with 0 tokens)")
            return

        # Update session
        session_id = interaction.parsed_request.session_id
        logger.info(f"[_store_interaction] session_id={session_id}, in_active={session_id in self.state.active_sessions}")
        if log_manager:
            log_manager.log_debug(f"[_store_interaction] session_id={session_id}, in_active={session_id in self.state.active_sessions}")
        if session_id in self.state.active_sessions:
            session = self.state.active_sessions[session_id]
            session.total_requests += 1
            session.total_input_tokens += interaction.input_tokens
            session.total_output_tokens += interaction.output_tokens
            session.total_cost += interaction.cost
            session.ended_at = datetime.now()
            self.db.upsert_session(session)
            logger.info(f"[_store_interaction] Updated session: total_requests={session.total_requests}")
            if log_manager:
                log_manager.log_debug(f"[_store_interaction] Updated session: total_requests={session.total_requests}")

        # Extract parsed response content
        response_text = ""
        response_thinking = ""
        if interaction.parsed_response:
            response_text = interaction.parsed_response.text_content
            response_thinking = interaction.parsed_response.thinking_content

        # Extract timing info from flow
        timing = self._extract_timing_info(flow) if flow else {}

        # Deduplicate system-reminder content
        try:
            body_dict = json.loads(interaction.request_body) if interaction.request_body else {}
            processed_body = AnthropicHandler.deduplicate_request_body(body_dict, self.db)
            request_body_to_store = json.dumps(processed_body)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to deduplicate system-reminder: {e}")
            request_body_to_store = interaction.request_body

        # Store tool calls with timing info if present
        tool_calls = []
        if interaction.parsed_response:
            tool_uses = interaction.parsed_response.get_tool_uses()
            tool_call_start_time = interaction.timestamp  # Use request timestamp as start
            for idx, tool_use in enumerate(tool_uses):
                tool_call = ToolCall(
                    request_id=interaction.request_id,
                    tool_name=tool_use.get("name", ""),
                    tool_input_json=json.dumps(tool_use.get("input", {})),
                    timestamp_start=tool_call_start_time,
                    timestamp_end=datetime.now(),  # End time when captured
                    duration_ms=None,  # Will be calculated when tool result is received
                )
                tool_calls.append(tool_call)

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
            request_body=request_body_to_store,
            response_body="",  # Skip streaming response body to save space
            response_text=response_text,
            response_thinking=response_thinking,
            # Timing fields
            connect_ms=timing.get('connect_ms'),
            tls_ms=timing.get('tls_ms'),
            send_ms=timing.get('send_ms'),
            wait_ms=timing.get('wait_ms'),
            receive_ms=timing.get('receive_ms'),
            # Streaming timing fields
            time_to_first_token_ms=self._calc_time_to_first_token(timing.get('wait_ms'), parsed_response),
            time_to_last_token_ms=self._calc_time_to_last_token(timing.get('wait_ms'), parsed_response),
            avg_token_latency_ms=self._calc_avg_token_latency(parsed_response),
            # Response headers
            response_headers=json.dumps(interaction.response_headers) if interaction.response_headers else None,
            x_request_id=interaction.x_request_id,
            anthropic_version=interaction.anthropic_version,
            ratelimit_limit=interaction.ratelimit_limit,
            ratelimit_remaining=interaction.ratelimit_remaining,
            ratelimit_reset=interaction.ratelimit_reset,
        )

        # Enqueue request for async write (instead of synchronous)
        enqueue_write((request, tool_calls))

        logger.debug(f"Enqueued request for writing: {interaction.request_id}")

    def done(self):
        """Called when the proxy is shutting down."""
        log_manager = get_log_manager()
        if log_manager:
            log_manager.log_info("Shutting down AnthropicCaptureAddon...")

        # Shutdown cleanup scheduler
        if self.cleanup_scheduler:
            try:
                self.cleanup_scheduler.stop(timeout=5.0)
                logger.info("Cleanup scheduler stopped")
                log_manager.log_info("Cleanup scheduler stopped")
            except Exception as e:
                logger.warning(f"Error stopping cleanup scheduler: {e}")
                log_manager.log_warning(f"Error stopping cleanup scheduler: {e}")

        # Disconnect SocketIO client
        if self._socketio_client and self._socketio_client.connected:
            try:
                self._socketio_client.disconnect()
                logger.info("SocketIO client disconnected")
                log_manager.log_info("SocketIO client disconnected")
            except Exception as e:
                logger.warning(f"Error disconnecting SocketIO client: {e}")
                log_manager.log_warning(f"Error disconnecting SocketIO client: {e}")

        # Shutdown write worker and flush pending items
        shutdown_worker(timeout=10.0)

        if log_manager:
            log_manager.log_info("AnthropicCaptureAddon shutdown complete")


# Export addon for mitmproxy
addons = [AnthropicCaptureAddon()]