#!/usr/bin/env python3
"""
Internal script to run the web server.
Called by run.py
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from web.app import app, db
from config.settings import WEB_HOST


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000, help="Web server port")
    args = parser.parse_args()

    # Run Flask app
    app.run(host=WEB_HOST, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()