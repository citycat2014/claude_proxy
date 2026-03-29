#!/bin/bash
# MCP Playwright 工具包装脚本

MCP_URL="http://localhost:8931"
SESSION_FILE="/tmp/mcp_playwright_session"
SSE_PID_FILE="/tmp/mcp_playwright_sse_pid"

# 启动 SSE 会话
start_session() {
    if [ -f "$SSE_PID_FILE" ]; then
        local pid=$(cat "$SSE_PID_FILE" 2>/dev/null)
        if kill -0 "$pid" 2>/dev/null; then
            echo "Session already active"
            return 0
        fi
    fi

    # 清理旧文件
    rm -f /tmp/mcp_sse_*.txt

    # 启动 SSE 连接
    local sse_file="/tmp/mcp_sse_$$.txt"
    curl -s -N "$MCP_URL/sse" > "$sse_file" 2>/dev/null &
    local sse_pid=$!
    echo $sse_pid > "$SSE_PID_FILE"

    sleep 3

    # 提取 sessionId
    local session_id=$(grep -o 'sessionId=[^ ]*' "$sse_file" | head -1 | cut -d'=' -f2)
    if [ -z "$session_id" ]; then
        echo "Failed to get session ID"
        kill $sse_pid 2>/dev/null
        rm -f "$SSE_PID_FILE"
        return 1
    fi

    echo "$session_id" > "$SESSION_FILE"
    echo "$sse_file" >> "$SESSION_FILE"

    # 初始化 MCP
    curl -s "$MCP_URL/mcp?sessionId=$session_id" \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"claude","version":"1.0"}},"id":1}' \
        > /dev/null

    echo "Session started: $session_id"
    return 0
}

# 调用 MCP 工具
call_tool() {
    local tool_name=$1
    shift
    local args=""

    # 构建参数 JSON
    while [[ $# -gt 0 ]]; do
        local key=$1
        local val=$2
        if [[ "$val" == "true" || "$val" == "false" ]]; then
            args="$args\"$key\":$val,"
        elif [[ "$val" =~ ^[0-9]+$ ]]; then
            args="$args\"$key\":$val,"
        else
            args="$args\"$key\":\"$val\","
        fi
        shift 2
    done
    args="{${args%,}}"

    local session_id=$(head -1 "$SESSION_FILE" 2>/dev/null)
    if [ -z "$session_id" ]; then
        echo "No active session. Run: $0 start"
        return 1
    fi

    local payload=$(cat <<EOF
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"$tool_name","arguments":$args},"id":$(date +%s)}
EOF
)

    curl -s "$MCP_URL/mcp?sessionId=$session_id" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload"
}

# 关闭会话
stop_session() {
    if [ -f "$SSE_PID_FILE" ]; then
        local pid=$(cat "$SSE_PID_FILE" 2>/dev/null)
        kill $pid 2>/dev/null
        rm -f "$SSE_PID_FILE"
    fi
    rm -f "$SESSION_FILE"
    rm -f /tmp/mcp_sse_*.txt
    echo "Session stopped"
}

# 主命令
case "$1" in
    start)
        start_session
        ;;
    stop)
        stop_session
        ;;
    navigate)
        call_tool "playwright_navigate" "$@"
        ;;
    screenshot)
        call_tool "playwright_screenshot" "$@"
        ;;
    click)
        call_tool "playwright_click" "$@"
        ;;
    fill)
        call_tool "playwright_fill" "$@"
        ;;
    close)
        call_tool "playwright_close"
        stop_session
        ;;
    *)
        echo "Usage: $0 {start|stop|navigate|screenshot|click|fill|close}"
        echo ""
        echo "Examples:"
        echo "  $0 start                                  # 启动会话"
        echo "  $0 navigate url https://www.baidu.com     # 导航到百度"
        echo "  $0 screenshot name myshot fullPage true   # 截图"
        echo "  $0 close                                  # 关闭浏览器并结束会话"
        ;;
esac
