#!/usr/bin/env python3
"""
Add composite indexes to existing database for better query performance.

Run this script once to add the new indexes to your existing database.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import Database
from config.settings import DATABASE_PATH
import sqlite3


def add_indexes(db_path: str):
    """Add composite indexes to the database."""
    print(f"Adding indexes to database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # List of indexes to create
    indexes = [
        ("idx_requests_session_timestamp",
         "CREATE INDEX IF NOT EXISTS idx_requests_session_timestamp ON requests(session_id, timestamp DESC)"),
        ("idx_requests_model_timestamp",
         "CREATE INDEX IF NOT EXISTS idx_requests_model_timestamp ON requests(model, timestamp DESC)"),
    ]

    for index_name, create_sql in indexes:
        try:
            cursor.execute(create_sql)
            conn.commit()
            print(f"✓ Created index: {index_name}")
        except sqlite3.Error as e:
            print(f"✗ Error creating index {index_name}: {e}")

    # Verify indexes
    print("\nVerifying indexes...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='requests'")
    existing_indexes = cursor.fetchall()

    print("\nIndexes on requests table:")
    for idx in existing_indexes:
        print(f"  - {idx[0]}")

    conn.close()
    print("\n✓ Index migration completed!")


if __name__ == "__main__":
    add_indexes(DATABASE_PATH)
