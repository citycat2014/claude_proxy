#!/usr/bin/env python3
"""
Unified management script for Claude Code Capture.

Usage:
    python scripts/run.py start [--proxy-port 8080] [--web-port 5000]
    python scripts/run.py stop
    python scripts/run.py restart
    python scripts/run.py status
"""

import argparse
import subprocess
import sys
import os
import signal
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Default ports
DEFAULT_PROXY_PORT = 8080
DEFAULT_WEB_PORT = 5000

# PID files
PID_DIR = Path(__file__).parent.parent / "data" / "pids"
PROXY_PID_FILE = PID_DIR / "proxy.pid"
WEB_PID_FILE = PID_DIR / "web.pid"


def ensure_pid_dir():
    """Ensure PID directory exists."""
    PID_DIR.mkdir(parents=True, exist_ok=True)


def write_pid(pid_file: Path, pid: int):
    """Write PID to file."""
    ensure_pid_dir()
    pid_file.write_text(str(pid))


def read_pid(pid_file: Path) -> int | None:
    """Read PID from file."""
    if pid_file.exists():
        try:
            return int(pid_file.read_text().strip())
        except ValueError:
            return None
    return None


def remove_pid(pid_file: Path):
    """Remove PID file."""
    if pid_file.exists():
        pid_file.unlink()


def is_process_running(pid: int) -> bool:
    """Check if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def start_proxy(proxy_port: int, web_port: int) -> bool:
    """Start the proxy server."""
    pid = read_pid(PROXY_PID_FILE)
    if pid and is_process_running(pid):
        print(f"Proxy already running (PID: {pid})")
        return True

    print(f"Starting proxy server on port {proxy_port}...")

    # Set environment variables for the subprocess
    env = os.environ.copy()
    env["PROXY_PORT"] = str(proxy_port)
    env["WEB_PORT"] = str(web_port)

    # Start proxy in background
    script_dir = Path(__file__).parent
    proxy_script = script_dir / "_run_proxy.py"

    # Create log file for capturing errors
    ensure_pid_dir()
    log_file = PID_DIR / "proxy.log"

    with open(log_file, "w") as log_f:
        process = subprocess.Popen(
            [sys.executable, str(proxy_script), "--port", str(proxy_port)],
            stdout=log_f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )

    write_pid(PROXY_PID_FILE, process.pid)

    # Give it a moment to start
    time.sleep(0.5)

    if is_process_running(process.pid):
        print(f"✓ Proxy started (PID: {process.pid})")
        return True
    else:
        print("✗ Failed to start proxy")
        # Show log content for debugging
        if log_file.exists():
            log_content = log_file.read_text()
            if log_content.strip():
                print(f"\n  Error log:")
                for line in log_content.strip().split("\n")[:10]:
                    print(f"    {line}")
        return False


def start_web(web_port: int) -> bool:
    """Start the web server."""
    pid = read_pid(WEB_PID_FILE)
    if pid and is_process_running(pid):
        print(f"Web server already running (PID: {pid})")
        return True

    print(f"Starting web server on port {web_port}...")

    # Set environment variables
    env = os.environ.copy()
    env["WEB_PORT"] = str(web_port)

    script_dir = Path(__file__).parent
    web_script = script_dir / "_run_web.py"

    process = subprocess.Popen(
        [sys.executable, str(web_script), "--port", str(web_port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )

    write_pid(WEB_PID_FILE, process.pid)

    # Give it a moment to start
    time.sleep(0.5)

    if is_process_running(process.pid):
        print(f"✓ Web server started (PID: {process.pid})")
        print(f"  Dashboard: http://127.0.0.1:{web_port}")
        return True
    else:
        print("✗ Failed to start web server")
        return False


def stop_service(pid_file: Path, name: str) -> bool:
    """Stop a service by PID file."""
    pid = read_pid(pid_file)

    if not pid:
        print(f"{name} is not running")
        return True

    if not is_process_running(pid):
        remove_pid(pid_file)
        print(f"{name} is not running (stale PID file removed)")
        return True

    print(f"Stopping {name} (PID: {pid})...")

    try:
        # Send SIGTERM
        os.killpg(os.getpgid(pid), signal.SIGTERM)

        # Wait for process to terminate
        for _ in range(10):
            if not is_process_running(pid):
                break
            time.sleep(0.2)

        # Force kill if still running
        if is_process_running(pid):
            os.killpg(os.getpgid(pid), signal.SIGKILL)
            time.sleep(0.2)

        if not is_process_running(pid):
            remove_pid(pid_file)
            print(f"✓ {name} stopped")
            return True
        else:
            print(f"✗ Failed to stop {name}")
            return False

    except ProcessLookupError:
        remove_pid(pid_file)
        print(f"✓ {name} stopped (process not found)")
        return True
    except Exception as e:
        print(f"✗ Error stopping {name}: {e}")
        return False


def kill_processes_on_port(port: int) -> bool:
    """Kill any processes listening on the given port."""
    try:
        # Use lsof to find processes on the port
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0 or not result.stdout.strip():
            return False

        pids = [int(p.strip()) for p in result.stdout.strip().split("\n") if p.strip()]

        if not pids:
            return False

        print(f"  Found {len(pids)} process(es) on port {port}")

        killed = []
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                killed.append(pid)
            except (OSError, ProcessLookupError):
                pass

        # Wait for processes to terminate
        time.sleep(0.5)

        # Force kill if still running
        for pid in pids:
            try:
                os.kill(pid, 0)  # Check if still running
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.2)
            except (OSError, ProcessLookupError):
                pass

        if killed:
            print(f"  ✓ Killed process(es): {', '.join(map(str, killed))}")
            return True

    except Exception as e:
        print(f"  ✗ Error killing processes on port {port}: {e}")

    return False


def stop_all(proxy_port: int = DEFAULT_PROXY_PORT, web_port: int = DEFAULT_WEB_PORT):
    """Stop all services and clean up ports."""
    stop_service(PROXY_PID_FILE, "Proxy")
    stop_service(WEB_PID_FILE, "Web server")

    # Clean up any zombie processes on ports
    print("\nCleaning up ports...")
    kill_processes_on_port(proxy_port)
    kill_processes_on_port(web_port)


def restart_all(proxy_port: int = DEFAULT_PROXY_PORT, web_port: int = DEFAULT_WEB_PORT):
    """Restart all services."""
    print("Claude Code Capture - Restarting...")
    print("=" * 40)
    stop_all(proxy_port, web_port)
    time.sleep(1)  # Give ports time to release
    start_proxy(proxy_port, web_port)
    start_web(web_port)
    print("=" * 40)
    print("\n✓ All services restarted!")
    print(f"\nConfigure Claude Code:")
    print(f"  export HTTPS_PROXY=http://127.0.0.1:{proxy_port}")
    print(f"  export HTTP_PROXY=http://127.0.0.1:{proxy_port}")
    print(f"\nDashboard: http://127.0.0.1:{web_port}")


def show_status():
    """Show status of all services."""
    print("Service Status:")
    print("-" * 40)

    # Proxy status
    proxy_pid = read_pid(PROXY_PID_FILE)
    if proxy_pid and is_process_running(proxy_pid):
        print(f"  Proxy:    Running (PID: {proxy_pid})")
    else:
        print("  Proxy:    Not running")

    # Web status
    web_pid = read_pid(WEB_PID_FILE)
    if web_pid and is_process_running(web_pid):
        print(f"  Web:      Running (PID: {web_pid})")
    else:
        print("  Web:      Not running")

    print("-" * 40)

    # Usage info
    if proxy_pid and is_process_running(proxy_pid):
        print("\nTo use with Claude Code:")
        print("  export HTTPS_PROXY=http://127.0.0.1:8080")
        print("  export HTTP_PROXY=http://127.0.0.1:8080")


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code Capture - Unified management script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start                    Start with default ports
  %(prog)s start -p 8888 -w 3000    Start with custom ports
  %(prog)s stop                     Stop all services
  %(prog)s status                   Show service status
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start all services")
    start_parser.add_argument(
        "-p", "--proxy-port",
        type=int,
        default=DEFAULT_PROXY_PORT,
        help=f"Proxy port (default: {DEFAULT_PROXY_PORT})"
    )
    start_parser.add_argument(
        "-w", "--web-port",
        type=int,
        default=DEFAULT_WEB_PORT,
        help=f"Web UI port (default: {DEFAULT_WEB_PORT})"
    )

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop all services")
    stop_parser.add_argument(
        "-p", "--proxy-port",
        type=int,
        default=DEFAULT_PROXY_PORT,
        help=f"Proxy port to clean up (default: {DEFAULT_PROXY_PORT})"
    )
    stop_parser.add_argument(
        "-w", "--web-port",
        type=int,
        default=DEFAULT_WEB_PORT,
        help=f"Web UI port to clean up (default: {DEFAULT_WEB_PORT})"
    )

    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart all services")
    restart_parser.add_argument(
        "-p", "--proxy-port",
        type=int,
        default=DEFAULT_PROXY_PORT,
        help=f"Proxy port (default: {DEFAULT_PROXY_PORT})"
    )
    restart_parser.add_argument(
        "-w", "--web-port",
        type=int,
        default=DEFAULT_WEB_PORT,
        help=f"Web UI port (default: {DEFAULT_WEB_PORT})"
    )

    # Status command
    subparsers.add_parser("status", help="Show service status")

    args = parser.parse_args()

    if args.command == "start":
        print("Claude Code Capture - Starting...")
        print("=" * 40)

        success = True
        if not start_proxy(args.proxy_port, args.web_port):
            success = False
        if not start_web(args.web_port):
            success = False

        print("=" * 40)

        if success:
            print("\n✓ All services started successfully!")
            print(f"\nConfigure Claude Code:")
            print(f"  export HTTPS_PROXY=http://127.0.0.1:{args.proxy_port}")
            print(f"  export HTTP_PROXY=http://127.0.0.1:{args.proxy_port}")
            print(f"\nDashboard: http://127.0.0.1:{args.web_port}")
        else:
            print("\n✗ Some services failed to start")
            sys.exit(1)

    elif args.command == "stop":
        print("Claude Code Capture - Stopping...")
        print("=" * 40)
        stop_all(args.proxy_port, args.web_port)
        print("=" * 40)
        print("\n✓ All services stopped")

    elif args.command == "restart":
        restart_all(args.proxy_port, args.web_port)

    elif args.command == "status":
        show_status()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()