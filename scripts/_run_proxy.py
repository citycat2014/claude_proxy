#!/usr/bin/env python3
"""
Internal script to run the proxy server.
Called by run.py
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from config.settings import PROXY_HOST
from proxy.addon import AnthropicCaptureAddon


async def run_proxy(port: int):
    """Run the proxy server."""
    opts = Options(listen_host=PROXY_HOST, listen_port=port)

    master = DumpMaster(opts)
    master.addons.add(AnthropicCaptureAddon())

    try:
        await master.run()
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080, help="Proxy port")
    args = parser.parse_args()

    asyncio.run(run_proxy(args.port))


if __name__ == "__main__":
    main()