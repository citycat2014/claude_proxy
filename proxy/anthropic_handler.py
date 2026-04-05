"""
Anthropic API request and response handler.

Handles parsing of API requests and responses, extracting relevant information
for storage and analysis.
"""

import json
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from config.settings import PRICING
from proxy.stream_parser import SSEParser, ParsedResponse

logger = logging.getLogger(__name__)


@dataclass
class ParsedRequest:
    """Parsed API request."""
    request_id: str
    session_id: str
    model: str
    system_prompt: str
    messages: List[Dict[str, Any]]
    tools: List[Dict[str, Any]]
    max_tokens: int
    is_streaming: bool
    raw_body: Dict[str, Any]

    # Extracted info
    user_agent: str = ""
    working_directory: str = ""


@dataclass
class APIInteraction:
    """Complete API interaction (request + response)."""
    request_id: str
    session_id: str
    timestamp: datetime

    # Request
    parsed_request: ParsedRequest

    # Response
    response_status: int
    response_time_ms: int
    parsed_response: Optional[ParsedResponse] = None

    # Raw data
    request_body: str = ""
    response_body: str = ""

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    # Cost
    cost: float = 0.0

    # Response headers (captured for rate limiting and debugging)
    response_headers: Dict[str, str] = None
    x_request_id: str = ""
    anthropic_version: str = ""
    ratelimit_limit: int = 0
    ratelimit_remaining: int = 0
    ratelimit_reset: int = 0

    def __post_init__(self):
        if self.response_headers is None:
            self.response_headers = {}

    def calculate_cost(self):
        """Calculate the cost of this interaction."""
        model = self.parsed_request.model
        pricing = PRICING.get(model, PRICING.get("default", {}))

        input_cost = (self.input_tokens / 1_000_000) * pricing.get("input", 0)
        output_cost = (self.output_tokens / 1_000_000) * pricing.get("output", 0)
        cache_write_cost = (self.cache_creation_tokens / 1_000_000) * pricing.get("cache_write", 0)
        cache_read_cost = (self.cache_read_tokens / 1_000_000) * pricing.get("cache_read", 0)

        self.cost = input_cost + output_cost + cache_write_cost + cache_read_cost


class AnthropicHandler:
    """Handler for Anthropic API requests and responses."""

    def __init__(self):
        self._pending_requests: Dict[str, Dict[str, Any]] = {}
        self._stream_parsers: Dict[str, SSEParser] = {}

    def parse_request(
        self,
        method: str,
        endpoint: str,
        headers: Dict[str, str],
        body: bytes,
    ) -> Optional[ParsedRequest]:
        """
        Parse an API request.

        Args:
            method: HTTP method
            endpoint: API endpoint
            headers: Request headers
            body: Request body

        Returns:
            ParsedRequest or None if not a valid Anthropic request
        """
        if not body:
            return None

        try:
            raw_body = json.loads(body)
        except json.JSONDecodeError:
            return None

        # Generate request ID
        request_id = raw_body.get("id") or self._generate_request_id(body)

        # Extract session ID from headers or generate
        session_id = self._extract_session_id(headers, raw_body)

        # Parse messages
        messages = raw_body.get("messages", [])
        logger.info(f"Parsed {len(messages)} messages from request")

        if messages:
            last_msg = messages[-1] if messages else None
            if last_msg and last_msg.get("role") == "user":
                content = last_msg.get("content", "")
                logger.info(f"Last user message content preview: {str(content)[:200]}")

        # Extract system prompt
        system_prompt = raw_body.get("system", "")
        if isinstance(system_prompt, list):
            # Handle structured system prompt
            system_prompt = "\n".join(
                block.get("text", "")
                for block in system_prompt
                if block.get("type") == "text"
            )

        # Extract tools
        tools = raw_body.get("tools", [])

        # Check if streaming
        is_streaming = raw_body.get("stream", False)

        # Extract metadata
        user_agent = headers.get("user-agent", "")
        working_directory = self._extract_working_directory(messages)

        return ParsedRequest(
            request_id=request_id,
            session_id=session_id,
            model=raw_body.get("model", ""),
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            max_tokens=raw_body.get("max_tokens", 0),
            is_streaming=is_streaming,
            raw_body=raw_body,
            user_agent=user_agent,
            working_directory=working_directory,
        )

    def handle_response_start(
        self,
        request_id: str,
        status: int,
        headers: Dict[str, str],
    ):
        """
        Handle the start of a response.

        Args:
            request_id: The request ID
            status: HTTP status code
            headers: Response headers
        """
        self._pending_requests[request_id] = {
            "status": status,
            "headers": headers,
            "chunks": [],
            "start_time": datetime.now(),
        }

        # Check if streaming
        content_type = headers.get("content-type", "")
        if "text/event-stream" in content_type or "application/stream+json" in content_type:
            self._stream_parsers[request_id] = SSEParser()

    def handle_response_chunk(self, request_id: str, chunk: bytes):
        """
        Handle a chunk of response data.

        Args:
            request_id: The request ID
            chunk: Response chunk
        """
        if request_id in self._pending_requests:
            self._pending_requests[request_id]["chunks"].append(chunk)

        if request_id in self._stream_parsers:
            self._stream_parsers[request_id].feed(chunk)

    def handle_response_end(self, request_id: str) -> Optional[APIInteraction]:
        """
        Handle the end of a response.

        Args:
            request_id: The request ID

        Returns:
            APIInteraction if successful, None otherwise
        """
        pending = self._pending_requests.pop(request_id, None)
        if not pending:
            return None

        stream_parser = self._stream_parsers.pop(request_id, None)

        # Calculate response time
        start_time = pending["start_time"]
        response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Combine chunks
        chunks = pending["chunks"]
        full_response = b"".join(chunks)

        # Parse response
        parsed_response = None
        response_body = ""

        if stream_parser:
            # Streaming response
            parsed_response = stream_parser.get_response()
            response_body = json.dumps(parsed_response.to_dict())
        else:
            # Non-streaming response
            try:
                response_body = full_response.decode("utf-8")
                response_data = json.loads(response_body)
                parsed_response = self._parse_non_streaming_response(response_data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        return APIInteraction(
            request_id=request_id,
            session_id="",  # Will be set from parsed_request
            timestamp=start_time,
            parsed_request=ParsedRequest(
                request_id=request_id,
                session_id="",
                model="",
                system_prompt="",
                messages=[],
                tools=[],
                max_tokens=0,
                is_streaming=False,
                raw_body={},
            ),
            response_status=pending["status"],
            response_time_ms=response_time_ms,
            parsed_response=parsed_response,
            response_body=response_body,
        )

    def create_interaction(
        self,
        parsed_request: ParsedRequest,
        response_status: int,
        response_time_ms: int,
        response_body: bytes,
        response_headers: Optional[Dict[str, str]] = None,
    ) -> APIInteraction:
        """
        Create an APIInteraction from request and response data.

        Args:
            parsed_request: Parsed request
            response_status: HTTP status code
            response_time_ms: Response time in milliseconds
            response_body: Response body bytes
            response_headers: Optional response headers dict

        Returns:
            APIInteraction
        """
        # Parse response
        parsed_response = None
        response_body_str = ""

        try:
            response_body_str = response_body.decode("utf-8")
            response_data = json.loads(response_body_str)

            if parsed_request.is_streaming:
                # Handle streaming response that was already collected
                pass
            else:
                parsed_response = self._parse_non_streaming_response(response_data)

        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        interaction = APIInteraction(
            request_id=parsed_request.request_id,
            session_id=parsed_request.session_id,
            timestamp=datetime.now(),
            parsed_request=parsed_request,
            response_status=response_status,
            response_time_ms=response_time_ms,
            parsed_response=parsed_response,
            response_body=response_body_str,
        )

        # Parse response headers if provided
        if response_headers:
            interaction.response_headers = response_headers
            interaction.x_request_id = response_headers.get("x-request-id", "")
            interaction.anthropic_version = response_headers.get("anthropic-version", "")

            # Parse rate limit headers
            if "anthropic-ratelimit-limit" in response_headers:
                try:
                    interaction.ratelimit_limit = int(response_headers["anthropic-ratelimit-limit"])
                except ValueError:
                    pass
            if "anthropic-ratelimit-remaining" in response_headers:
                try:
                    interaction.ratelimit_remaining = int(response_headers["anthropic-ratelimit-remaining"])
                except ValueError:
                    pass
            if "anthropic-ratelimit-reset" in response_headers:
                try:
                    # Reset time might be Unix timestamp or seconds
                    reset_value = response_headers["anthropic-ratelimit-reset"]
                    interaction.ratelimit_reset = int(float(reset_value))
                except (ValueError, TypeError):
                    pass

        return interaction

        return interaction

    def _parse_non_streaming_response(self, data: Dict[str, Any]) -> ParsedResponse:
        """Parse a non-streaming response."""
        from proxy.stream_parser import ContentBlock

        response = ParsedResponse()
        response.message_id = data.get("id", "")
        response.model = data.get("model", "")
        response.role = data.get("role", "assistant")
        response.stop_reason = data.get("stop_reason", "")
        response.stop_sequence = data.get("stop_sequence", "")

        # Parse content
        for idx, block in enumerate(data.get("content", [])):
            block_type = block.get("type", "text")
            content_block = ContentBlock(
                index=idx,
                block_type=block_type,
            )

            if block_type == "text":
                content_block.text = block.get("text", "")
            elif block_type == "tool_use":
                content_block.tool_use_id = block.get("id", "")
                content_block.tool_name = block.get("name", "")
                content_block.tool_input = block.get("input", {})

            response.content_blocks.append(content_block)

        # Parse usage
        usage = data.get("usage", {})
        response.input_tokens = usage.get("input_tokens", 0)
        response.output_tokens = usage.get("output_tokens", 0)
        response.cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
        response.cache_read_tokens = usage.get("cache_read_input_tokens", 0)

        return response

    def _generate_request_id(self, body: bytes) -> str:
        """Generate a unique request ID from body content and timestamp."""
        import time
        # Include timestamp to ensure uniqueness for identical requests
        unique_content = body + str(time.time_ns()).encode()
        hash_obj = hashlib.md5(unique_content)
        return f"req_{hash_obj.hexdigest()[:16]}"

    def _extract_session_id(
        self,
        headers: Dict[str, str],
        body: Dict[str, Any]
    ) -> str:
        """Extract or generate a session ID."""
        # Try to extract from metadata
        metadata = body.get("metadata", {})
        if metadata:
            # Try standard session_id/conversation_id fields
            session_id = metadata.get("session_id") or metadata.get("conversation_id")
            if session_id:
                return session_id

            # Extract from user_id field (Claude Code format: user_xxx_session_uuid)
            user_id = metadata.get("user_id", "")
            if "_session_" in user_id:
                # Extract UUID after _session_
                parts = user_id.split("_session_")
                if len(parts) > 1:
                    return parts[1]

        # Try headers
        for header in ["x-session-id", "x-conversation-id", "anthropic-session-id"]:
            if header in headers:
                return headers[header]

        # Generate based on content hash (group related requests)
        messages = body.get("messages", [])
        if messages:
            first_user_msg = ""
            for msg in messages:
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        first_user_msg = content[:100]
                    elif isinstance(content, list):
                        for block in content:
                            if block.get("type") == "text":
                                text = block.get("text", "")
                                # Skip system-reminder prefix
                                if text.startswith("<system-reminder>"):
                                    # Find the actual user message after system-reminder
                                    continue
                                first_user_msg = text[:100]
                                break
                    break

            if first_user_msg:
                hash_obj = hashlib.md5(first_user_msg.encode())
                return hash_obj.hexdigest()[:12]

        # Fallback to daily session
        today = datetime.now().strftime("%Y%m%d")
        return today

    def _extract_working_directory(self, messages: List[Dict[str, Any]]) -> str:
        """Extract working directory from messages if present."""
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_use":
                        tool_input = block.get("input", {})
                        if "working_directory" in tool_input:
                            return tool_input["working_directory"]
                        if "file_path" in tool_input:
                            # Extract directory from file path
                            import os
                            return os.path.dirname(tool_input["file_path"])
        return ""

    @staticmethod
    def extract_system_reminder(text: str) -> Tuple[str, Optional[str]]:
        """
        Extract system-reminder block from text.

        Returns:
            Tuple of (cleaned_text, system_reminder_content or None)
        """
        if "<system-reminder>" not in text:
            return text, None

        # Find all system-reminder blocks
        import re
        pattern = r'<system-reminder>.*?</system-reminder>'
        matches = re.findall(pattern, text, re.DOTALL)

        if not matches:
            return text, None

        # Remove system-reminder blocks from text
        cleaned = re.sub(pattern, '', text, flags=re.DOTALL).strip()

        # Concatenate all system-reminder content
        system_content = '\n'.join(matches)

        return cleaned, system_content

    @staticmethod
    def deduplicate_request_body(body: Dict[str, Any], db) -> Dict[str, Any]:
        """
        Process request body to deduplicate system-reminder content.

        Args:
            body: Request body dict
            db: Database instance with save_system_reminder method

        Returns:
            Processed body with system-reminder references
        """
        if not body or "messages" not in body:
            return body

        messages = body.get("messages", [])
        if not messages:
            return body

        processed_messages = []
        for msg in messages:
            if msg.get("role") != "user":
                processed_messages.append(msg)
                continue

            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle array content
                processed_blocks = []
                for block in content:
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        cleaned, system_reminder = AnthropicHandler.extract_system_reminder(text)
                        if system_reminder and db:
                            # Save to deduplication table
                            content_hash = db.save_system_reminder(system_reminder)
                            # Replace with reference
                            block["text"] = f"[SYSTEM_REMINDER_REF:{content_hash}]\n{cleaned}".strip()
                        else:
                            block["text"] = cleaned
                        processed_blocks.append(block)
                    else:
                        processed_blocks.append(block)
                msg["content"] = processed_blocks
            elif isinstance(content, str):
                # Handle string content
                cleaned, system_reminder = AnthropicHandler.extract_system_reminder(content)
                if system_reminder and db:
                    content_hash = db.save_system_reminder(system_reminder)
                    msg["content"] = f"[SYSTEM_REMINDER_REF:{content_hash}]\n{cleaned}".strip()
                else:
                    msg["content"] = cleaned

            processed_messages.append(msg)

        body["messages"] = processed_messages
        return body


# Singleton instance
handler = AnthropicHandler()