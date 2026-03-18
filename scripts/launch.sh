#!/usr/bin/env bash
# launch.sh — Launch a single agent via SDK adapter
#
# Usage:
#   ./scripts/launch.sh                                    # main agent, claude adapter
#   ./scripts/launch.sh --adapter codex                    # main agent, codex adapter
#   ./scripts/launch.sh --agent-dir agent/agents/reviewer  # sub-agent
#   ./scripts/launch.sh --task "Review PR #42"             # headless mode

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Defaults
ADAPTER="claude"
AGENT_DIR="$REPO_ROOT/agent"
TASK=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --adapter)
            ADAPTER="$2"
            shift 2
            ;;
        --agent-dir)
            AGENT_DIR="$2"
            shift 2
            ;;
        --task)
            TASK="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

LAUNCHER="$REPO_ROOT/agent/adapters/$ADAPTER/launcher.py"

if [ ! -f "$LAUNCHER" ]; then
    echo "❌ Adapter not found: $ADAPTER"
    echo "Available adapters: claude, codex, kimicode"
    exit 1
fi

echo "🚀 Launching agent..."
echo "  Adapter: $ADAPTER"
echo "  Agent dir: $AGENT_DIR"
[ -n "$TASK" ] && echo "  Task: $TASK"
echo ""

CMD="uv run $LAUNCHER --agent-dir $AGENT_DIR"
[ -n "$TASK" ] && CMD="$CMD --task \"$TASK\""

eval "$CMD"
