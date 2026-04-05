#!/usr/bin/env python3
"""
Database migration script to add response header columns and tool call timing columns.

Adds the following columns:
- requests.response_headers (JSON string of response headers)
- requests.x_request_id (Anthropic request ID)
- requests.ratelimit_limit, ratelimit_remaining, ratelimit_reset (rate limiting)
- requests.anthropic_version (API version)
- tool_calls.timestamp_start, timestamp_end (tool timing)

Usage:
    python scripts/migrate_response_headers.py
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DATABASE_PATH
from sqlalchemy import create_engine, text, inspect

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_column_if_not_exists(engine, table_name, column_name, column_def):
    """Add a column if it doesn't exist."""
    if check_column_exists(engine, table_name, column_name):
        print(f"  - Column {table_name}.{column_name} already exists")
        return False
    else:
        print(f"  - Adding column {table_name}.{column_name}...")
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}"))
            conn.commit()
        return True

def migrate():
    """Run database migration."""
    print(f"Database migration: Adding response header and tool timing columns")
    print(f"Database: {DATABASE_PATH}")
    print()

    engine = create_engine(f'sqlite:///{DATABASE_PATH}')

    # Request table columns
    print("Adding columns to 'requests' table:")
    request_columns = [
        ("response_headers", "response_headers TEXT"),
        ("x_request_id", "x_request_id VARCHAR(255)"),
        ("ratelimit_limit", "ratelimit_limit INTEGER"),
        ("ratelimit_remaining", "ratelimit_remaining INTEGER"),
        ("ratelimit_reset", "ratelimit_reset INTEGER"),
        ("anthropic_version", "anthropic_version VARCHAR(50)"),
    ]

    for col_name, col_def in request_columns:
        add_column_if_not_exists(engine, "requests", col_name, col_def)

    print()
    print("Adding columns to 'tool_calls' table:")
    tool_columns = [
        ("timestamp_start", "timestamp_start DATETIME"),
        ("timestamp_end", "timestamp_end DATETIME"),
    ]

    for col_name, col_def in tool_columns:
        add_column_if_not_exists(engine, "tool_calls", col_name, col_def)

    print()
    print("Migration completed successfully!")
    print()
    print("Note: The storage/models.py already includes these fields in the Request and ToolCall models.")
    print("      New data will be captured automatically. Existing records will have NULL values for these fields.")

if __name__ == "__main__":
    migrate()
