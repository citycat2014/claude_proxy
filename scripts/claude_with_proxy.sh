#!/bin/bash
# Claude Code with Proxy
# Usage:
#   方式1 - 直接运行: ./scripts/claude_with_proxy.sh
#   方式2 - source: source scripts/claude_with_proxy.sh && claude

export HTTP_PROXY=http://127.0.0.1:8080
export HTTPS_PROXY=http://127.0.0.1:8080
export http_proxy=http://127.0.0.1:8080
export https_proxy=http://127.0.0.1:8080

# 可选：信任 mitmproxy 证书（如果 Claude Code 使用 Node.js）
export NODE_EXTRA_CA_CERTS="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"

echo "✅ Proxy configured:"
echo "   HTTP_PROXY=$HTTP_PROXY"
echo "   HTTPS_PROXY=$HTTPS_PROXY"
echo ""

# 检查代理是否运行
if ! lsof -i:8080 > /dev/null 2>&1; then
    echo "⚠️  Warning: Proxy is not running on port 8080"
    echo "   Start proxy first: python scripts/run.py start"
    echo ""
fi

# 如果是直接运行（不是 source），则启动 claude
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "🚀 Starting Claude Code with proxy..."
    echo ""
    claude "$@"
else
    # 被 source 调用，只设置环境变量
    echo "Environment variables set."
    echo "Now run: claude"
fi