"""
SSE (Server-Sent Events) stream parser for Anthropic API streaming responses.

Handles parsing of streaming response events and reconstructing the complete response.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ContentBlock:
    """A content block in the response."""
    index: int
    block_type: str
    text: str = ""
    tool_use_id: str = ""
    tool_name: str = ""
    tool_input: Dict[str, Any] = field(default_factory=dict)
    tool_input_partial: str = ""  # For accumulating partial JSON


@dataclass
class ParsedResponse:
    """Parsed streaming response."""
    message_id: str = ""
    model: str = ""
    role: str = "assistant"
    stop_reason: str = ""
    stop_sequence: str = ""

    # Content blocks
    content_blocks: List[ContentBlock] = field(default_factory=list)

    # Usage
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    # Raw events for debugging
    events: List[Dict[str, Any]] = field(default_factory=list)

    # Accumulated content (for convenience)
    text_content: str = ""  # 累积的文本内容
    thinking_content: str = ""  # 累积的思考内容

    # Timing metrics
    first_token_time: Optional[datetime] = None
    last_token_time: Optional[datetime] = None
    token_count: int = 0
    total_generation_ms: int = 0

    def get_text_content(self) -> str:
        """Get all text content from response."""
        texts = []
        for block in self.content_blocks:
            if block.block_type == "text" and block.text:
                texts.append(block.text)
        return "\n".join(texts)

    def get_tool_uses(self) -> List[Dict[str, Any]]:
        """Get all tool use blocks."""
        tools = []
        for block in self.content_blocks:
            if block.block_type == "tool_use":
                tools.append({
                    "id": block.tool_use_id,
                    "name": block.tool_name,
                    "input": block.tool_input,
                })
        return tools

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        content = []
        for block in self.content_blocks:
            if block.block_type == "text":
                content.append({
                    "type": "text",
                    "text": block.text,
                })
            elif block.block_type == "tool_use":
                content.append({
                    "type": "tool_use",
                    "id": block.tool_use_id,
                    "name": block.tool_name,
                    "input": block.tool_input,
                })

        return {
            "id": self.message_id,
            "type": "message",
            "role": self.role,
            "content": content,
            "model": self.model,
            "stop_reason": self.stop_reason,
            "stop_sequence": self.stop_sequence,
            "usage": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cache_creation_input_tokens": self.cache_creation_tokens,
                "cache_read_input_tokens": self.cache_read_tokens,
            },
        }


class SSEParser:
    """Parser for Anthropic API SSE streaming responses."""

    def __init__(self):
        self.response = ParsedResponse()
        self._current_block: Optional[ContentBlock] = None
        self._start_time: Optional[datetime] = None

    def feed(self, chunk: bytes) -> List[Dict[str, Any]]:
        """
        Feed a chunk of data to the parser.

        Args:
            chunk: Raw bytes from the stream

        Returns:
            List of parsed events
        """
        # Initialize start time on first feed
        if self._start_time is None:
            self._start_time = datetime.now()

        events = []

        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            return events

        for line in text.split("\n"):
            line = line.strip()

            if not line:
                continue

            if line.startswith("data:"):
                # Handle both "data:" and "data: " formats
                data = line[5:].strip() if line[5:6] == " " else line[5:]
                if data:
                    try:
                        event = json.loads(data)
                        events.append(event)
                        self._process_event(event)
                        self.response.events.append(event)
                    except json.JSONDecodeError:
                        # Handle partial JSON if needed
                        pass
            elif line.startswith("event: "):
                # Event type line, usually followed by data
                pass

        return events

    def _process_event(self, event: Dict[str, Any]):
        """Process a single SSE event."""
        event_type = event.get("type", "")

        if event_type == "message_start":
            self._handle_message_start(event)
        elif event_type == "content_block_start":
            self._handle_content_block_start(event)
        elif event_type == "content_block_delta":
            self._handle_content_block_delta(event)
        elif event_type == "content_block_stop":
            self._handle_content_block_stop(event)
        elif event_type == "message_delta":
            self._handle_message_delta(event)
        elif event_type == "message_stop":
            self._handle_message_stop(event)

    def _handle_message_start(self, event: Dict[str, Any]):
        """Handle message_start event."""
        message = event.get("message", {})
        self.response.message_id = message.get("id", "")
        self.response.model = message.get("model", "")
        self.response.role = message.get("role", "assistant")

        usage = message.get("usage", {})
        self.response.input_tokens = usage.get("input_tokens", 0)
        self.response.cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
        self.response.cache_read_tokens = usage.get("cache_read_input_tokens", 0)

    def _handle_content_block_start(self, event: Dict[str, Any]):
        """Handle content_block_start event."""
        index = event.get("index", 0)
        content_block = event.get("content_block", {})
        block_type = content_block.get("type", "text")

        self._current_block = ContentBlock(
            index=index,
            block_type=block_type,
        )

        if block_type == "tool_use":
            self._current_block.tool_use_id = content_block.get("id", "")
            self._current_block.tool_name = content_block.get("name", "")
        elif block_type == "thinking":
            # Thinking block - text field will accumulate thinking content
            pass

    def _handle_content_block_delta(self, event: Dict[str, Any]):
        """Handle content_block_delta event."""
        if not self._current_block:
            return

        index = event.get("index", 0)
        delta = event.get("delta", {})

        # Ensure we're on the right block
        if self._current_block.index != index:
            return

        delta_type = delta.get("type", "")

        if delta_type == "text_delta":
            # Accumulate text
            text = delta.get("text", "")
            self._current_block.text += text
            self.response.text_content += text
            # Record token timing
            self._record_token()

        elif delta_type == "input_json_delta":
            # Accumulate tool input JSON
            self._current_block.tool_input_partial += delta.get("partial_json", "")

        elif delta_type == "thinking_delta":
            # Accumulate thinking
            thinking = delta.get("thinking", "")
            self._current_block.text += thinking
            self.response.thinking_content += thinking
            # Record token timing
            self._record_token()

    def _handle_content_block_stop(self, event: Dict[str, Any]):
        """Handle content_block_stop event."""
        if not self._current_block:
            return

        index = event.get("index", 0)

        if self._current_block.index == index:
            # Finalize tool input if needed
            if (self._current_block.block_type == "tool_use"
                and self._current_block.tool_input_partial):
                try:
                    self._current_block.tool_input = json.loads(
                        self._current_block.tool_input_partial
                    )
                except json.JSONDecodeError:
                    self._current_block.tool_input = {
                        "_error": "Failed to parse JSON",
                        "_raw": self._current_block.tool_input_partial,
                    }

            # Add to response
            self.response.content_blocks.append(self._current_block)
            self._current_block = None

    def _handle_message_delta(self, event: Dict[str, Any]):
        """Handle message_delta event."""
        delta = event.get("delta", {})
        self.response.stop_reason = delta.get("stop_reason", "")
        self.response.stop_sequence = delta.get("stop_sequence", "")

        usage = event.get("usage", {})
        self.response.output_tokens = usage.get("output_tokens", 0)
        # Also update input_tokens if present (final count)
        if "input_tokens" in usage:
            self.response.input_tokens = usage["input_tokens"]
        if "cache_creation_input_tokens" in usage:
            self.response.cache_creation_tokens = usage["cache_creation_input_tokens"]
        if "cache_read_input_tokens" in usage:
            self.response.cache_read_tokens = usage["cache_read_input_tokens"]

    def _handle_message_stop(self, event: Dict[str, Any]):
        """Handle message_stop event."""
        # Message is complete, finalize timing
        if self._start_time and self.response.last_token_time:
            self.response.total_generation_ms = int(
                (self.response.last_token_time - self.response.first_token_time).total_seconds() * 1000
            )

    def _record_token(self):
        """Record a token arrival time."""
        now = datetime.now()
        if self.response.first_token_time is None:
            self.response.first_token_time = now
        self.response.last_token_time = now
        self.response.token_count += 1

    def get_response(self) -> ParsedResponse:
        """Get the parsed response."""
        return self.response

    def reset(self):
        """Reset the parser for a new response."""
        self.response = ParsedResponse()
        self._current_block = None


def parse_streaming_response(chunks: List[bytes]) -> ParsedResponse:
    """
    Convenience function to parse a complete streaming response.

    Args:
        chunks: List of byte chunks from the stream

    Returns:
        ParsedResponse object
    """
    parser = SSEParser()
    for chunk in chunks:
        parser.feed(chunk)
    return parser.get_response()