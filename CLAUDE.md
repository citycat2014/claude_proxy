# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pkts_capture** is a tool for capturing and analyzing interactions between Claude Code and the Anthropic API on macOS. It uses mitmproxy as an HTTPS proxy to intercept API traffic and stores the data in SQLite for analysis via a Flask web dashboard.

## Common Commands

### Service Management
```bash
# Start proxy and web services (default ports: proxy 8080, web 5000)
python scripts/run.py start

# Start with custom ports
python scripts/run.py start -p 8888 -w 3000

# Stop all services
python scripts/run.py stop

# Check service status
python scripts/run.py status
```

### Environment Setup
```bash
# Set up environment for current shell (exports SSL_CERT_FILE, HTTPS_PROXY, etc.)
source scripts/init_env.sh

# Check certificate and service status
scripts/init_env.sh --check

# Install shell aliases to ~/.zshrc
scripts/init_env.sh --install
```

### Manual Proxy Usage
```bash
# After sourcing init_env.sh, run Claude Code with proxy enabled
claude

# Or use the convenience script
scripts/claude_with_proxy.sh
```

## Architecture Overview

### Data Flow

```
Claude Code → HTTPS Proxy (mitmproxy) → Anthropic API
                    ↓
              addon.py (AnthropicCaptureAddon)
                    ↓
           anthropic_handler.py (parse request/response)
                    ↓
           stream_parser.py (parse SSE streaming)
                    ↓
           storage/database.py (SQLite)
                    ↓
           web/app.py (Flask dashboard)
```

### Module Structure

**proxy/** - MITM proxy interception
- `addon.py` - Main mitmproxy addon (`AnthropicCaptureAddon`), entry point for all intercepted traffic
- `anthropic_handler.py` - Parses Anthropic API requests/responses, extracts tokens, tools, costs
- `stream_parser.py` - Parses Server-Sent Events (SSE) streaming responses

**storage/** - Data persistence
- `database.py` - SQLite operations, schema initialization, CRUD for sessions/requests/tool_calls
- `models.py` - Dataclasses: `Session`, `Request`, `ToolCall`, `Message`, `Statistics`

**web/** - Dashboard
- `app.py` - Flask app with REST API endpoints (`/api/statistics/*`, `/api/sessions/*`, `/api/analysis/*`)
- `templates/` - Jinja2 HTML templates
- `static/` - CSS/JS assets

**analysis/** - Data analysis
- `token_analyzer.py` - Token usage analysis by model, cost estimation
- `tool_analyzer.py` - Tool usage patterns and performance
- `statistics.py` - Summary statistics and timeline generation

**config/** - Configuration
- `settings.py` - All settings including `TARGET_DOMAINS`, `PRICING` (per-million-token costs), port configs

**scripts/** - Management utilities
- `run.py` - Unified CLI for start/stop/status, manages PID files in `data/pids/`
- `init_env.sh` - Shell environment setup, certificate trust
- `_run_proxy.py` / `_run_web.py` - Internal wrappers called by `run.py`

### Key Data Models

**Session** - A Claude Code session (identified by metadata or content hash)
**Request** - Single API call with full request/response bodies, token counts, cost
**ToolCall** - Tool usage within a request

### Target Domains

The proxy intercepts traffic to these domains (configured in `config/settings.py`):
- `api.anthropic.com` - Main Anthropic API
- `dashscope.aliyuncs.com` - Alibaba Cloud Claude proxy
- `statsig.anthropic.com`, `sentry.io` - Telemetry

### Port Configuration

- Proxy: 8080 (configurable via `-p` or `PROXY_PORT` env)
- Web dashboard: 5000 (configurable via `-w` or `WEB_PORT` env)

### Database

SQLite database stored at `data/capture.db` (configurable via `DATABASE_PATH` env). Schema includes tables for sessions, requests, tool_calls, messages, statistics.

### Certificate Handling

mitmproxy generates certificates at `~/.mitmproxy/mitmproxy-ca-cert.pem`. The `init_env.sh` script sets `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` to trust this certificate.

## Development Notes

- No test suite exists currently
- Uses `sys.path.insert(0, ...)` pattern for imports from project root
- Database schema is auto-initialized on first connection
- Proxy addon uses flow metadata (`flow.metadata["is_tracked"]`) to track request/response pairs
- Streaming responses use SSE (Server-Sent Events) format parsing

## Important Lessons Learned

### Timezone Consistency

**Critical**: All timestamp fields must use consistent timezone handling. The project uses local time (not UTC) for all timestamps.

- `Request.timestamp` - Uses `datetime.now()` (local time) set in `proxy/anthropic_handler.py`
- `ToolCall.timestamp` - Must use `datetime.now()` (not `datetime.utcnow()`) in model default
- `Session.started_at/ended_at` - Uses local time

**Bug Example**: When ToolCall used `datetime.utcnow()` as default while Request used local time, time-based queries returned inconsistent results (e.g., "last 1 hour" showing requests but no tool calls because of 8-hour timezone difference).

**Fix**: Ensure all `DateTime` columns in `storage/models.py` use `default=datetime.now` (without timezone conversion).
