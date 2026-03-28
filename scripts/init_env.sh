#!/bin/bash
#
# Initialize environment for Claude Code Capture
#
# Usage:
#   source scripts/init_env.sh        # Set up current shell
#   scripts/init_env.sh --install     # Add to shell profile
#

# Project root
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Default values
DEFAULT_PROXY_PORT=8080
DEFAULT_WEB_PORT=5000

# Certificate path
CERT_PATH="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════╗"
    echo "║     Claude Code Capture - Environment      ║"
    echo "╚════════════════════════════════════════════╝"
    echo ""
}

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Export environment variables for current shell
export_env() {
    local proxy_port="${1:-$DEFAULT_PROXY_PORT}"

    # Export certificate paths
    export SSL_CERT_FILE="$CERT_PATH"
    export REQUESTS_CA_BUNDLE="$CERT_PATH"
    export NODE_EXTRA_CA_CERTS="$CERT_PATH"

    # Export proxy settings
    export HTTPS_PROXY="http://127.0.0.1:$proxy_port"
    export HTTP_PROXY="http://127.0.0.1:$proxy_port"
    export ALL_PROXY="http://127.0.0.1:$proxy_port"

    # Export project path
    export CLAUDE_CAPTURE_ROOT="$PROJECT_ROOT"
}

# Print current status
show_status() {
    echo "Current environment:"
    echo ""
    echo "  SSL_CERT_FILE:         ${SSL_CERT_FILE:-<not set>}"
    echo "  REQUESTS_CA_BUNDLE:    ${REQUESTS_CA_BUNDLE:-<not set>}"
    echo "  NODE_EXTRA_CA_CERTS:   ${NODE_EXTRA_CA_CERTS:-<not set>}"
    echo "  HTTPS_PROXY:           ${HTTPS_PROXY:-<not set>}"
    echo "  HTTP_PROXY:            ${HTTP_PROXY:-<not set>}"
    echo ""
}

# Check certificate exists
check_cert() {
    if [ -f "$CERT_PATH" ]; then
        print_status "Certificate found: $CERT_PATH"
        return 0
    else
        print_warning "Certificate not found: $CERT_PATH"
        echo ""
        echo "  Run 'python scripts/run.py start' first to generate the certificate."
        return 1
    fi
}

# Check services running
check_services() {
    local proxy_running=false
    local web_running=false

    if lsof -i :${DEFAULT_PROXY_PORT} >/dev/null 2>&1; then
        proxy_running=true
    fi

    if lsof -i :${DEFAULT_WEB_PORT} >/dev/null 2>&1; then
        web_running=true
    fi

    echo "Service status:"
    echo ""
    if $proxy_running; then
        print_status "Proxy running on port $DEFAULT_PROXY_PORT"
    else
        print_warning "Proxy not running on port $DEFAULT_PROXY_PORT"
    fi

    if $web_running; then
        print_status "Web UI running on port $DEFAULT_WEB_PORT"
    else
        print_warning "Web UI not running on port $DEFAULT_WEB_PORT"
    fi
    echo ""
}

# Install to shell profile
install_to_profile() {
    local profile=""
    local shell_name=$(basename "$SHELL")

    if [ "$shell_name" = "zsh" ]; then
        profile="$HOME/.zshrc"
    elif [ "$shell_name" = "bash" ]; then
        profile="$HOME/.bashrc"
    else
        print_error "Unsupported shell: $shell_name"
        return 1
    fi

    # Check if already installed
    if grep -q "CLAUDE_CAPTURE_ROOT" "$profile" 2>/dev/null; then
        print_warning "Already installed in $profile"
        return 0
    fi

    echo ""
    echo "Installing to $profile..."
    echo ""

    cat >> "$profile" << 'ENVMARKER'

# Claude Code Capture environment
export CLAUDE_CAPTURE_ROOT="__PROJECT_ROOT__"
export SSL_CERT_FILE="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"
export REQUESTS_CA_BUNDLE="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"
export NODE_EXTRA_CA_CERTS="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"

# Claude Code Capture alias
alias claude-capture-start='python $CLAUDE_CAPTURE_ROOT/scripts/run.py start'
alias claude-capture-stop='python $CLAUDE_CAPTURE_ROOT/scripts/run.py stop'
alias claude-capture-status='python $CLAUDE_CAPTURE_ROOT/scripts/run.py status'

# Function to enable proxy
claude-proxy-on() {
    export HTTPS_PROXY="http://127.0.0.1:8080"
    export HTTP_PROXY="http://127.0.0.1:8080"
    export ALL_PROXY="http://127.0.0.1:8080"
    echo "✓ Proxy enabled: http://127.0.0.1:8080"
}

# Function to disable proxy
claude-proxy-off() {
    unset HTTPS_PROXY HTTP_PROXY ALL_PROXY
    echo "✓ Proxy disabled"
}
ENVMARKER

    # Replace placeholder with actual path
    sed -i '' "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" "$profile"

    print_status "Installed to $profile"
    echo ""
    echo "  Run 'source $profile' or start a new shell to apply."
    echo ""
}

# Uninstall from shell profile
uninstall_from_profile() {
    local profile=""
    local shell_name=$(basename "$SHELL")

    if [ "$shell_name" = "zsh" ]; then
        profile="$HOME/.zshrc"
    elif [ "$shell_name" = "bash" ]; then
        profile="$HOME/.bashrc"
    else
        print_error "Unsupported shell: $shell_name"
        return 1
    fi

    if [ -f "$profile" ]; then
        # Remove the block between markers
        if grep -q "Claude Code Capture environment" "$profile"; then
            # Create temp file without the block
            sed '/^# Claude Code Capture environment/,/^$/d' "$profile" > "$profile.tmp"
            mv "$profile.tmp" "$profile"
            print_status "Removed from $profile"
        else
            print_warning "Not found in $profile"
        fi
    fi
}

# Show usage
show_usage() {
    echo "Usage:"
    echo ""
    echo "  source scripts/init_env.sh           Set up environment for current shell"
    echo "  scripts/init_env.sh --install        Add to shell profile (~/.zshrc)"
    echo "  scripts/init_env.sh --uninstall      Remove from shell profile"
    echo "  scripts/init_env.sh --status         Show current status"
    echo "  scripts/init_env.sh --check          Check certificate and services"
    echo ""
    echo "After sourcing, use these commands:"
    echo ""
    echo "  claude-proxy-on          Enable proxy for Claude Code"
    echo "  claude-proxy-off         Disable proxy"
    echo "  claude-capture-start     Start capture services"
    echo "  claude-capture-stop      Stop capture services"
    echo "  claude-capture-status    Show service status"
    echo ""
}

# Main
main() {
    print_banner

    case "${1:-}" in
        --install|-i)
            check_cert
            install_to_profile
            ;;
        --uninstall|-u)
            uninstall_from_profile
            ;;
        --status|-s)
            show_status
            ;;
        --check|-c)
            check_cert
            echo ""
            check_services
            ;;
        --help|-h)
            show_usage
            ;;
        "")
            # Default: export for current shell
            export_env
            check_cert
            echo ""
            echo "Environment configured for current shell:"
            echo "  SSL_CERT_FILE=$SSL_CERT_FILE"
            echo "  HTTPS_PROXY=$HTTPS_PROXY"
            echo ""
            echo "Now you can run: claude"
            ;;
        *)
            print_error "Unknown option: $1"
            echo ""
            show_usage
            return 1
            ;;
    esac
}

# Run main if not being sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]] || [[ "${ZSH_EVAL_CONTEXT:-}" == "file" ]]; then
    main "$@"
fi