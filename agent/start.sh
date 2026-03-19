#!/usr/bin/env bash
# start.sh — Unified launch entry point (dev mode)
# Check .runtime/ -> select adapter -> start agent
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$AGENT_DIR/.." && pwd)"

# Default parameters
ROLE=""
ADAPTER="claude"
WORKSPACE=".socialware/workspace/default"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --role) ROLE="$2"; shift 2 ;;
        --adapter) ADAPTER="$2"; shift 2 ;;
        --workspace) WORKSPACE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

RUNTIME_DIR="$REPO_ROOT/$WORKSPACE/.runtime"

# 1. Check if .runtime/ exists; auto-deploy if not
if [ ! -d "$RUNTIME_DIR/agents" ]; then
    echo "No .runtime/ found. Running deploy.sh..."
    "$AGENT_DIR/deploy.sh" "$WORKSPACE"
    echo ""
fi

# 2. Determine which roles to start
if [ -z "$ROLE" ]; then
    # List all available roles
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
        echo "No shell adapter for $ADAPTER. Use --mode sdk or src/start_agent.py"
        exit 1
    fi
else
    # Multiple roles — tmux multi-pane
    SESSION="socialware-$(date +%s)"
    echo "Starting ${#ROLES[@]} roles in tmux session: $SESSION"

    # Create tmux session with first role
    first_role="${ROLES[0]}"
    first_dir="$RUNTIME_DIR/agents/$first_role"
    tmux new-session -d -s "$SESSION" "$ADAPTER_DIR/shell.sh $first_dir"

    # Create new panes for remaining roles
    for ((i=1; i<${#ROLES[@]}; i++)); do
        role_name="${ROLES[$i]}"
        project_dir="$RUNTIME_DIR/agents/$role_name"
        tmux split-window -t "$SESSION" -h "$ADAPTER_DIR/shell.sh $project_dir"
        tmux select-layout -t "$SESSION" tiled
    done

    echo "Attaching to tmux session..."
    exec tmux attach -t "$SESSION"
fi
