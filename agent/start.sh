#!/usr/bin/env bash
# start.sh — 统一启动入口 (开发模式)
# 检查 .runtime/ → 选择 adapter → 启动 agent
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$AGENT_DIR/.." && pwd)"

# 默认参数
ROLE=""
ADAPTER="claude"
WORKSPACE=".socialware/workspace/default"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --role) ROLE="$2"; shift 2 ;;
        --adapter) ADAPTER="$2"; shift 2 ;;
        --workspace) WORKSPACE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

RUNTIME_DIR="$REPO_ROOT/$WORKSPACE/.runtime"

# 1. 检查 .runtime/ 是否存在，不存在则自动 deploy
if [ ! -d "$RUNTIME_DIR/agents" ]; then
    echo "No .runtime/ found. Running deploy.sh..."
    "$AGENT_DIR/deploy.sh" "$WORKSPACE"
    echo ""
fi

# 2. 确定要启动的 roles
if [ -z "$ROLE" ]; then
    # 列出所有可用 role
    echo "Available roles:"
    for role_dir in "$RUNTIME_DIR"/agents/*/; do
        [ -d "$role_dir" ] || continue
        echo "  - $(basename "$role_dir")"
    done
    echo ""
    echo "Usage: ./agent/start.sh --role <name>[,name2]"
    exit 0
fi

# 3. 解析 role 列表
IFS=',' read -ra ROLES <<< "$ROLE"

# 4. 检查 adapter 是否存在
ADAPTER_DIR="$AGENT_DIR/adapters/$ADAPTER"
if [ ! -d "$ADAPTER_DIR" ]; then
    echo "Adapter not found: $ADAPTER"
    echo "Available: claude, codex, kimicode"
    exit 1
fi

# 5. 启动
if [ ${#ROLES[@]} -eq 1 ]; then
    # 单 role — 直接启动
    role_name="${ROLES[0]}"
    project_dir="$RUNTIME_DIR/agents/$role_name"

    if [ ! -d "$project_dir" ]; then
        echo "Role not found: $role_name"
        exit 1
    fi

    echo "Starting $role_name via $ADAPTER adapter..."
    echo "  PROJECT_DIR: $project_dir"
    echo ""

    if [ -f "$ADAPTER_DIR/shell.sh" ]; then
        exec "$ADAPTER_DIR/shell.sh" "$project_dir"
    else
        echo "No shell adapter for $ADAPTER. Use --mode sdk or src/start_agent.py"
        exit 1
    fi
else
    # 多 role — tmux 多 pane
    SESSION="socialware-$(date +%s)"
    echo "Starting ${#ROLES[@]} roles in tmux session: $SESSION"

    # 创建 tmux session with first role
    first_role="${ROLES[0]}"
    first_dir="$RUNTIME_DIR/agents/$first_role"
    tmux new-session -d -s "$SESSION" "$ADAPTER_DIR/shell.sh $first_dir"

    # 为其余 role 创建新 pane
    for ((i=1; i<${#ROLES[@]}; i++)); do
        role_name="${ROLES[$i]}"
        project_dir="$RUNTIME_DIR/agents/$role_name"
        tmux split-window -t "$SESSION" -h "$ADAPTER_DIR/shell.sh $project_dir"
        tmux select-layout -t "$SESSION" tiled
    done

    echo "Attaching to tmux session..."
    exec tmux attach -t "$SESSION"
fi
