# Claude Code Capture

A tool for capturing and analyzing interactions between Claude Code and the Anthropic API on macOS.

## Features

- **HTTPS Proxy**: Intercepts all HTTP(S) traffic between Claude Code and Anthropic API
- **Request/Response Capture**: Records complete API interactions including streaming responses
- **Token Analysis**: Track token usage by model, session, and time period
- **Cost Tracking**: Calculate costs based on current Anthropic pricing
- **Tool Usage Analysis**: Analyze which tools are used and their performance
- **Web Dashboard**: Beautiful web interface for viewing and analyzing data

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start services
python scripts/run.py start

# 3. Initialize environment (set certificate + proxy)
source scripts/init_env.sh

# 4. Run Claude Code
claude
```

## Environment Setup

### Option 1: Temporary (Current Shell)

```bash
source scripts/init_env.sh
```

This sets:
- `SSL_CERT_FILE` - Certificate for TLS
- `REQUESTS_CA_BUNDLE` - Certificate for requests library
- `HTTPS_PROXY` / `HTTP_PROXY` - Proxy settings

### Option 2: Permanent (Shell Profile)

```bash
scripts/init_env.sh --install
source ~/.zshrc
```

This adds aliases to your shell:
- `claude-proxy-on` - Enable proxy
- `claude-proxy-off` - Disable proxy
- `claude-capture-start` - Start services
- `claude-capture-stop` - Stop services
- `claude-capture-status` - Show status

### Option 3: Manual Setup

```bash
export SSL_CERT_FILE=~/.mitmproxy/mitmproxy-ca-cert.pem
export REQUESTS_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem
export HTTPS_PROXY=http://127.0.0.1:8080
export HTTP_PROXY=http://127.0.0.1:8080
```

## Commands

```bash
# Start services
python scripts/run.py start                    # Default ports
python scripts/run.py start -p 8888 -w 3000   # Custom ports

# Stop services
python scripts/run.py stop

# Check status
python scripts/run.py status
```

## Environment Script

```bash
source scripts/init_env.sh           # Set up current shell
scripts/init_env.sh --install        # Add to ~/.zshrc
scripts/init_env.sh --uninstall      # Remove from ~/.zshrc
scripts/init_env.sh --status         # Show environment
scripts/init_env.sh --check          # Check cert + services
```

## Usage Flow

```bash
# Terminal 1: Start capture
python scripts/run.py start

# Terminal 2: Set environment + run Claude Code
source scripts/init_env.sh
claude

# View dashboard
open http://localhost:5000
```

## Project Structure

```
pkts_capture/
├── scripts/
│   ├── run.py          # Start/stop/status
│   ├── init_env.sh     # Environment setup
│   └── trust_cert.sh   # macOS certificate trust
├── proxy/              # MITM proxy
├── storage/            # SQLite database
├── analysis/           # Token/tool analysis
├── web/                # Web dashboard
└── data/               # Database + logs
```

## Troubleshooting

### TLS Handshake Failed

```
Client TLS handshake failed. The client does not trust the proxy's certificate.
```

**Solution:**
```bash
source scripts/init_env.sh
```

### Certificate Not Found

```bash
scripts/init_env.sh --check
```

If certificate missing, start proxy first:
```bash
python scripts/run.py start
```

### Port In Use

```bash
lsof -i :8080
python scripts/run.py start -p 8888
```

## API Endpoints

- `GET /api/statistics/summary` - Overall stats
- `GET /api/sessions` - Session list
- `GET /api/analysis/tokens` - Token analysis
- `GET /api/analysis/tools` - Tool analysis

## License

MIT