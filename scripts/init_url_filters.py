"""
Initialize default URL filters from TARGET_DOMAINS.

Run: python scripts/init_url_filters.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.database import Database
from config.settings import TARGET_DOMAINS


def init_default_filters():
    """Initialize default URL filters from config."""
    db = Database()

    # Check if filters already exist
    existing = db.get_url_filters(enabled_only=False)
    if existing:
        print(f"Found {len(existing)} existing filters. Skipping initialization.")
        print("Run with --force to reinitialize (will not delete existing).")
        return

    # Default filters based on TARGET_DOMAINS
    defaults = [
        {
            "name": "Anthropic API",
            "pattern": "api.anthropic.com",
            "filter_type": "domain",
            "action": "include",
            "priority": 10
        },
        {
            "name": "DashScope (Aliyun)",
            "pattern": "dashscope.aliyuncs.com",
            "filter_type": "domain",
            "action": "include",
            "priority": 20
        },
        {
            "name": "Statsig",
            "pattern": "statsig.anthropic.com",
            "filter_type": "domain",
            "action": "include",
            "priority": 100
        },
        {
            "name": "Sentry",
            "pattern": "sentry.io",
            "filter_type": "domain",
            "action": "include",
            "priority": 100
        },
        {
            "name": "Messages API Path",
            "pattern": "/v1/messages",
            "filter_type": "path",
            "action": "include",
            "priority": 5
        }
    ]

    print("Initializing default URL filters...")
    print(f"Target domains from config: {TARGET_DOMAINS}")
    print()

    for i, filter_data in enumerate(defaults, 1):
        try:
            db.add_url_filter(filter_data)
            print(f"  [{i}/{len(defaults)}] Added: {filter_data['name']} ({filter_data['pattern']})")
        except Exception as e:
            print(f"  [{i}/{len(defaults)}] Failed: {filter_data['name']} - {e}")

    print()
    print("=" * 60)
    print("Initialization complete!")
    print("=" * 60)
    print()
    print("You can manage filters in the web UI at:")
    print("  http://localhost:5000/settings")
    print()
    print("Or via API:")
    print("  GET    /api/url-filters       - List all filters")
    print("  POST   /api/url-filters       - Create new filter")
    print("  PUT    /api/url-filters/<id>  - Update filter")
    print("  DELETE /api/url-filters/<id>  - Delete filter")


if __name__ == "__main__":
    init_default_filters()
