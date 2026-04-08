"""
Configuration settings for pkts_capture.

All settings can be overridden via environment variables.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent.absolute()

# Proxy settings
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8080"))

# Web settings
WEB_HOST = os.getenv("WEB_HOST", "127.0.0.1")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Database settings
DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    str(BASE_DIR / "data" / "capture.db")
)

# Target API domains to intercept
TARGET_DOMAINS = [
    "api.anthropic.com",
    "statsig.anthropic.com",
    "sentry.io",
    "dashscope.aliyuncs.com",  # 阿里云 DashScope
    "coding.dashscope.aliyuncs.com",  # 阿里云 Claude Code 代理
]

# Anthropic API pricing (per million tokens, USD)
PRICING = {
    "claude-sonnet-4-20250514": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-opus-4-20250514": {
        "input": 15.00,
        "output": 75.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
    "claude-3-5-sonnet-20241022": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-3-5-sonnet-20240620": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-3-opus-20240229": {
        "input": 15.00,
        "output": 75.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
    "claude-3-sonnet-20240229": {
        "input": 3.00,
        "output": 15.00,
    },
    "claude-3-haiku-20240307": {
        "input": 0.25,
        "output": 1.25,
    },
    # Default fallback
    "default": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
}

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Session tracking
SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", "3600"))  # 1 hour

# Data retention settings
DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "30"))  # Days to retain full data
DATA_CLEANUP_ENABLED = os.getenv("DATA_CLEANUP_ENABLED", "true").lower() == "true"
DATA_CLEANUP_INTERVAL_HOURS = int(os.getenv("DATA_CLEANUP_INTERVAL_HOURS", "24"))
DATA_CLEANUP_BATCH_SIZE = int(os.getenv("DATA_CLEANUP_BATCH_SIZE", "100"))

# Recycle bin settings
RECYCLE_BIN_ENABLED = os.getenv("RECYCLE_BIN_ENABLED", "true").lower() == "true"
RECYCLE_BIN_RETENTION_DAYS = int(os.getenv("RECYCLE_BIN_RETENTION_DAYS", "7"))  # Days to keep data in recycle bin

# Claude API settings (from Claude Code config)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")