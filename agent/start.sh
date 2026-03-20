#!/usr/bin/env bash
# start.sh — Launch agent from the current workspace
#
# Works relative to its own location: agent/ in the same directory tree.
# No --workspace flag needed — just cd into your workspace and run.
#
# Usage (from within a workspace):
#   ./agent/start.sh --role default
#   ./agent/start.sh --role admin --adapter codex
#   ./agent/start.sh --role admin,reviewer     # multi-role -> tmux
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="$(cd "$AGENT_DIR/.." && pwd)"
RUNTIME_DIR="$APP_ROOT/.runtime"

# Default parameters
ROLE=""
ADAPTER="claude"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --role) ROLE="$2"; shift 2 ;;
        --adapter) ADAPTER="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# 1. Check if .runtime/ exists; prompt to deploy if not
if [ ! -d "$RUNTIME_DIR/agents" ]; then
    echo "No .runtime/ found at $RUNTIME_DIR"
    echo "Run ./agent/deploy.sh first."
    exit 1
fi

# 2. Determine which roles to start
if [ -z "$ROLE" ]; then
    echo "Available roles:"
    for role_dir in "$RUNTIME_DIR"/agents/*/; do
        [ -d "$role_dir" ] || continue
        echo "  - $(basename "$role_dir")"
    done
    echo ""
    echo "Usage: ./agent/start.sh --role <name>[,name2]"
    exit 0
fi

# 3. Parse role list
IFS=',' read -ra ROLES <<< "$ROLE"

# 4. Check if adapter exists
ADAPTER_DIR="$AGENT_DIR/adapters/$ADAPTER"
if [ ! -d "$ADAPTER_DIR" ]; then
    echo "Adapter not found: $ADAPTER"
    echo "Available: claude, codex, kimicode"
    exit 1
fi

# 5. Launch
if [ ${#ROLES[@]} -eq 1 ]; then
    # Single role — launch directly
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
        echo "No shell adapter for $ADAPTER. Use src/start_agent.py for SDK mode."
        exit 1
    fi
else
    # Multiple roles — tmux multi-pane
    SESSION="socialware-$(date +%s)"
    echo "Starting ${#ROLES[@]} roles in tmux session: $SESSION"

    first_role="${ROLES[0]}"
    first_dir="$RUNTIME_DIR/agents/$first_role"
    tmux new-session -d -s "$SESSION" "$ADAPTER_DIR/shell.sh $first_dir"

    for ((i=1; i<${#ROLES[@]}; i++)); do
        role_name="${ROLES[$i]}"
        project_dir="$RUNTIME_DIR/agents/$role_name"
        tmux split-window -t "$SESSION" -h "$ADAPTER_DIR/shell.sh $project_dir"
        tmux select-layout -t "$SESSION" tiled
    done

    echo "Attaching to tmux session..."
    exec tmux attach -t "$SESSION"
fi
